"""Transfer-learn a nail-condition classifier (MobileNetV3-Large, ImageNet init).

Trains on the NailCheck folder dataset (data/raw/nailcheck-3xvkl), restricted to
the conditions the app actually screens for. Saves weights + label list to
ml/models/ for the inference side (ml/infer/classifier.py) to load.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/train/train_classifier.py

What this does beyond a plain head-only transfer:
  - ROI crop: every image is cropped to the finger (same detector inference uses)
    before training, so the model learns the nail, not the dataset background.
  - Partial fine-tune: the classifier head trains fast (lr 1e-3) while the last
    backbone blocks fine-tune slowly (lr 1e-4) instead of staying frozen.
  - Class weights + label smoothing: handles the mild class imbalance and keeps
    the model from over-committing (which also helps calibration).
  - Phone-realistic augmentation: perspective + blur so it sees photo-like
    variation, not just clean dataset framing.
  - Temperature scaling: after training, one scalar is fit on the valid set so
    the probabilities inference gates on are calibrated, not raw softmax.
  - Reports a confusion matrix + per-class precision/recall. For a screener,
    recall on the condition classes (don't miss a real sign) is what matters.

HONESTY NOTE: NailCheck images are mostly top-down / frontal nail shots. This
model learns that view. Running it on a side-profile photo is a domain mismatch
-- treat side-view ML output with extra skepticism (the geometry track owns the
side profile). Accuracy reported here is on NailCheck's own held-out split, not
on real phone photos in the wild -- see ml/eval/eval_real.py for that.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
DATA = REPO / "data" / "raw" / "nailcheck-3xvkl"
MODELS = REPO / "ml" / "models"

from ml.infer.preprocessing import crop_to_finger_roi  # noqa: E402

# Folder names in the dataset -> the label we expose. Restricting to the app's
# current scope; add more pairs here to widen the classifier later.
CLASS_MAP = {
    "Clubbing": "clubbing",
    "Koilonychia": "koilonychia",
    "Healthy Nail": "healthy",
}
CLASSES = sorted(set(CLASS_MAP.values()))  # ['clubbing', 'healthy', 'koilonychia']
LABEL_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

BACKBONE = "mobilenet_v3_large"
IMG_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
EPOCHS = 18
BATCH = 32
LR_HEAD = 1e-3
LR_BACKBONE = 1e-4   # the unfrozen top blocks fine-tune ~10x slower than the head
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1
# How many of the backbone's trailing feature blocks to unfreeze for fine-tuning.
UNFREEZE_LAST_BLOCKS = 3


def _load_roi_rgb(path):
    """Decode -> crop to the finger ROI -> RGB float tensor in [0,1]."""
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"unreadable image: {path}")
    rgb = cv2.cvtColor(crop_to_finger_roi(bgr), cv2.COLOR_BGR2RGB)
    return torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float() / 255.0


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
        return self.tf(_load_roi_rgb(path)), label

    def class_counts(self):
        counts = [0] * len(CLASSES)
        for _, label in self.samples:
            counts[label] += 1
        return counts


def _train_tf():
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0), antialias=True),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
        transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.25, hue=0.02),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5)),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def _eval_tf():
    return transforms.Compose([
        transforms.Resize(256, antialias=True),
        transforms.CenterCrop(IMG_SIZE),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def build_model():
    model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
    # Freeze everything, then unfreeze the head + the last few feature blocks so
    # the model can adapt its high-level features to nails, not just remap them.
    for p in model.parameters():
        p.requires_grad = False
    for block in model.features[-UNFREEZE_LAST_BLOCKS:]:
        for p in block.parameters():
            p.requires_grad = True
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(CLASSES))  # new head: trainable
    return model


def param_groups(model):
    """Head (incl. the rest of the classifier) at LR_HEAD; backbone at LR_BACKBONE."""
    head, backbone = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        (head if name.startswith("classifier") else backbone).append(p)
    return [
        {"params": head, "lr": LR_HEAD},
        {"params": backbone, "lr": LR_BACKBONE},
    ]


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


def collect_logits(model, loader, device):
    model.eval()
    logits_all, y_all = [], []
    with torch.no_grad():
        for x, y in loader:
            logits_all.append(model(x.to(device)).cpu())
            y_all.append(y)
    return torch.cat(logits_all), torch.cat(y_all)


def fit_temperature(logits, y):
    """Single-parameter temperature scaling: minimize NLL of softmax(logits / T).

    A well-trained net is typically over-confident; dividing logits by T>1 cools
    the probabilities so the inference confidence floor means something.
    """
    log_t = torch.zeros(1, requires_grad=True)  # optimize log T to keep T > 0
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)
    nll = nn.CrossEntropyLoss()

    def closure():
        opt.zero_grad()
        loss = nll(logits / log_t.exp(), y)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.exp().item())


def report(logits, y, temperature):
    """Confusion matrix + per-class precision/recall on temperature-scaled probs."""
    n = len(CLASSES)
    preds = (logits / temperature).argmax(1)
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y.tolist(), preds.tolist()):
        cm[t][p] += 1

    print("\nconfusion matrix (rows = true, cols = predicted):")
    print("            " + "  ".join(f"{c[:7]:>7s}" for c in CLASSES))
    for i, c in enumerate(CLASSES):
        print(f"  {c:10s} " + "  ".join(f"{cm[i][j]:7d}" for j in range(n)))

    print("\nper-class precision / recall:")
    for i, c in enumerate(CLASSES):
        tp = cm[i][i]
        precision = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
        recall = tp / cm[i].sum() if cm[i].sum() else 0.0
        flag = "  <- recall on a condition class" if c != "healthy" else ""
        print(f"  {c:12s} P {precision:.3f}  R {recall:.3f}  (n={cm[i].sum()}){flag}")

    acc = np.trace(cm) / cm.sum()
    print(f"\noverall test accuracy {acc:.3f}")
    return acc


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} | backbone: {BACKBONE} | classes: {CLASSES}")

    train_ds = NailDataset("train", augment=True)
    valid_ds = NailDataset("valid", augment=False)
    test_ds = NailDataset("test", augment=False)
    print(f"Sizes -> train {len(train_ds)}, valid {len(valid_ds)}, test {len(test_ds)}")

    train_dl = DataLoader(train_ds, batch_size=BATCH, shuffle=True)
    valid_dl = DataLoader(valid_ds, batch_size=BATCH)
    test_dl = DataLoader(test_ds, batch_size=BATCH)

    # Class weights = inverse frequency, normalized -- counters the imbalance so
    # the model doesn't win by just predicting the majority class.
    counts = torch.tensor(train_ds.class_counts(), dtype=torch.float)
    weights = (counts.sum() / (len(CLASSES) * counts)).to(device)
    print(f"train class counts {counts.int().tolist()} | weights {weights.tolist()}")

    model = build_model().to(device)
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.Adam(param_groups(model), weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_acc, best_state = 0.0, None
    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_acc = run_epoch(model, train_dl, criterion, optimizer, device)
        va_loss, va_acc = run_epoch(model, valid_dl, criterion, None, device)
        scheduler.step()
        print(f"epoch {epoch:2d}  train_acc {tr_acc:.3f}  val_acc {va_acc:.3f}")
        if va_acc >= best_acc:
            best_acc, best_state = va_acc, {k: v.cpu() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)

    # Calibrate on the validation set (NOT test -- that would leak), then report
    # honest, calibrated numbers on the held-out test set.
    valid_logits, valid_y = collect_logits(model, valid_dl, device)
    temperature = fit_temperature(valid_logits, valid_y)
    print(f"\nBest val_acc {best_acc:.3f} | fitted temperature {temperature:.3f}")

    test_logits, test_y = collect_logits(model, test_dl, device)
    report(test_logits, test_y, temperature)

    MODELS.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, MODELS / "nail_classifier.pt")
    (MODELS / "nail_classifier_labels.json").write_text(
        json.dumps({"classes": CLASSES, "img_size": IMG_SIZE, "backbone": BACKBONE,
                    "mean": IMAGENET_MEAN, "std": IMAGENET_STD,
                    "temperature": round(temperature, 4)}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved -> {MODELS / 'nail_classifier.pt'}")


if __name__ == "__main__":
    main()
