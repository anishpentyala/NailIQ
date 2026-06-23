"""Transfer-learn a nail-condition classifier (MobileNetV3-Small, ImageNet init).

Trains on the NailCheck folder dataset (data/raw/nailcheck-3xvkl), restricted to
the conditions the app actually screens for. Saves weights + label list to
ml/models/ for the inference side (ml/infer/classifier.py) to load.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/train/train_classifier.py

CPU-friendly: the backbone is frozen and only the classifier head trains, so a
few epochs run in minutes without a GPU.

HONESTY NOTE: NailCheck images are mostly top-down / frontal nail shots. This
model learns that view. Running it on a side-profile photo is a domain mismatch
-- treat side-view ML output with extra skepticism (the geometry track owns the
side profile). Accuracy reported here is on NailCheck's own held-out split, not
on real phone photos in the wild.
"""

import json
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from torchvision.io import read_image, ImageReadMode

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "raw" / "nailcheck-3xvkl"
MODELS = REPO / "ml" / "models"

# Folder names in the dataset -> the label we expose. Restricting to the app's
# current scope; add more pairs here to widen the classifier later.
CLASS_MAP = {
    "Clubbing": "clubbing",
    "Koilonychia": "koilonychia",
    "Healthy Nail": "healthy",
}
CLASSES = sorted(set(CLASS_MAP.values()))  # ['clubbing', 'healthy', 'koilonychia']
LABEL_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

IMG_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
EPOCHS = 12
BATCH = 32
LR = 1e-3


class NailDataset(Dataset):
    def __init__(self, split, augment):
        self.samples = []
        for folder, label in CLASS_MAP.items():
            d = DATA / split / folder
            if not d.is_dir():
                continue
            for p in d.iterdir():
                if p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    self.samples.append((p, LABEL_TO_IDX[label]))
        if not self.samples:
            raise SystemExit(f"No images found under {DATA / split}. Did the download run?")
        self.tf = _train_tf() if augment else _eval_tf()

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        img = read_image(str(path), mode=ImageReadMode.RGB).float() / 255.0
        return self.tf(img), label


def _train_tf():
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def _eval_tf():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(IMG_SIZE),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def build_model():
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    for p in model.parameters():
        p.requires_grad = False
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(CLASSES))
    return model


def run_epoch(model, loader, criterion, optimizer, device):
    train = optimizer is not None
    model.train(train)
    total, correct, loss_sum = 0, 0, 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        with torch.set_grad_enabled(train):
            out = model(x)
            loss = criterion(out, y)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        loss_sum += loss.item() * x.size(0)
        correct += (out.argmax(1) == y).sum().item()
        total += x.size(0)
    return loss_sum / total, correct / total


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} | classes: {CLASSES}")

    train_ds = NailDataset("train", augment=True)
    valid_ds = NailDataset("valid", augment=False)
    test_ds = NailDataset("test", augment=False)
    print(f"Sizes -> train {len(train_ds)}, valid {len(valid_ds)}, test {len(test_ds)}")

    train_dl = DataLoader(train_ds, batch_size=BATCH, shuffle=True)
    valid_dl = DataLoader(valid_ds, batch_size=BATCH)
    test_dl = DataLoader(test_ds, batch_size=BATCH)

    model = build_model().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        (p for p in model.parameters() if p.requires_grad), lr=LR
    )

    best_acc, best_state = 0.0, None
    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_acc = run_epoch(model, train_dl, criterion, optimizer, device)
        va_loss, va_acc = run_epoch(model, valid_dl, criterion, None, device)
        print(f"epoch {epoch:2d}  train_acc {tr_acc:.3f}  val_acc {va_acc:.3f}")
        if va_acc > best_acc:
            best_acc, best_state = va_acc, {k: v.cpu() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    _, test_acc = run_epoch(model, test_dl, criterion, None, device)
    print(f"\nBest val_acc {best_acc:.3f} | test_acc {test_acc:.3f}")
    _per_class_report(model, test_dl, device)

    MODELS.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, MODELS / "nail_classifier.pt")
    (MODELS / "nail_classifier_labels.json").write_text(
        json.dumps({"classes": CLASSES, "img_size": IMG_SIZE,
                    "mean": IMAGENET_MEAN, "std": IMAGENET_STD}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved -> {MODELS / 'nail_classifier.pt'}")


def _per_class_report(model, loader, device):
    model.eval()
    n = len(CLASSES)
    hits = [0] * n
    counts = [0] * n
    with torch.no_grad():
        for x, y in loader:
            pred = model(x.to(device)).argmax(1).cpu()
            for yi, pi in zip(y, pred):
                counts[yi] += 1
                hits[yi] += int(yi == pi)
    print("per-class test accuracy:")
    for i, c in enumerate(CLASSES):
        acc = hits[i] / counts[i] if counts[i] else 0.0
        print(f"  {c:12s} {acc:.3f}  (n={counts[i]})")


if __name__ == "__main__":
    main()
