"""Transfer-learn a nail-condition classifier, ensemble-ready.

Trains ONE backbone per run and registers it in an ensemble manifest
(ml/models/nail_classifier_labels.json), so you build an ensemble by running this
a few times with different --backbone values. Inference (ml/infer/classifier.py)
averages whatever members the manifest lists.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/train/train_classifier.py --backbone mobilenet_v3_large
    backend/venv/Scripts/python.exe ml/train/train_classifier.py --backbone efficientnet_b0

Data: defaults to the merged dataset (data/raw/merged) if present, else the
original NailCheck classification folders (data/raw/nailcheck-3xvkl). Override with
--data-dir. Either way the layout is {train,valid,test}/{clubbing,koilonychia,
healthy}/ (NailCheck's folder names are mapped).

Recipe (all aimed at small-data generalization, mirrored at inference where it
matters so train/inference agree):
  - ROI crop cached once to <data_dir>__roicache (same finger crop inference does),
    so the CNN sees the nail not the background, without re-cropping every epoch.
  - RandAugment + RandomErasing + MixUp/CutMix for heavy regularization.
  - Partial fine-tune: last few backbone blocks unfreeze at a lower LR than the head.
  - AdamW, cosine schedule with linear warmup, EMA weights, early stopping.
  - Class weights + label smoothing for residual imbalance.
  - Temperature scaling fit on the validation set -> calibrated confidence.
  - Reports a confusion matrix + per-class precision/recall (recall on the
    condition classes is the screener metric to watch).

HONESTY NOTE: accuracy printed here is on the dataset's own held-out split, not on
real phone photos -- see ml/eval/eval_real.py for that.
"""

import argparse
import json
import random
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
MODELS = REPO / "ml" / "models"
LABELS_JSON = MODELS / "nail_classifier_labels.json"

from ml.infer.preprocessing import crop_to_finger_roi  # noqa: E402

# Accept both the merged dataset's lowercase folders and NailCheck's title-case ones.
FOLDER_TO_CLASS = {
    "clubbing": "clubbing", "Clubbing": "clubbing",
    "koilonychia": "koilonychia", "Koilonychia": "koilonychia",
    "healthy": "healthy", "Healthy Nail": "healthy",
}
CLASSES = sorted(set(FOLDER_TO_CLASS.values()))  # ['clubbing', 'healthy', 'koilonychia']
LABEL_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 224
BATCH = 32
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1
UNFREEZE_LAST_BLOCKS = 4
WARMUP_EPOCHS = 2
MIX_PROB = 0.5          # probability a batch gets MixUp/CutMix
MIX_ALPHA = 0.2         # Beta(alpha, alpha) for the mix ratio
EMA_DECAY = 0.999
PATIENCE = 6            # early-stop if val acc doesn't improve for this many epochs
SEED = 42

_EXTS = {".jpg", ".jpeg", ".png"}


def _default_data_dir():
    merged = REPO / "data" / "raw" / "merged"
    return merged if merged.is_dir() else REPO / "data" / "raw" / "nailcheck-3xvkl"


# ---- one-time ROI-crop cache -------------------------------------------------

def ensure_roi_cache(data_dir):
    """Mirror data_dir to <data_dir>__roicache with each image ROI-cropped once.

    crop_to_finger_roi runs the same finger detector inference uses; doing it here
    once (instead of every epoch) keeps train/inference parity cheap. Idempotent:
    skips files already cached.
    """
    cache = data_dir.parent / f"{data_dir.name}__roicache"
    todo = []
    for split in ("train", "valid", "test"):
        for folder in FOLDER_TO_CLASS:
            src = data_dir / split / folder
            if not src.is_dir():
                continue
            dst = cache / split / FOLDER_TO_CLASS[folder]
            dst.mkdir(parents=True, exist_ok=True)
            for p in src.iterdir():
                if p.suffix.lower() in _EXTS:
                    out = dst / (p.stem + ".jpg")
                    if not out.exists():
                        todo.append((p, out))
    if todo:
        print(f"ROI-cropping {len(todo)} new images into {cache.name} (one-time)...")
        for i, (p, out) in enumerate(todo):
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            cv2.imwrite(str(out), crop_to_finger_roi(bgr))
            if (i + 1) % 500 == 0:
                print(f"  {i + 1}/{len(todo)}")
    return cache


# ---- dataset -----------------------------------------------------------------

class NailDataset(Dataset):
    def __init__(self, cache_dir, split, augment):
        self.samples = []
        for cls in CLASSES:
            d = cache_dir / split / cls
            if not d.is_dir():
                continue
            for p in d.iterdir():
                if p.suffix.lower() in _EXTS:
                    self.samples.append((p, LABEL_TO_IDX[cls]))
        if not self.samples:
            raise SystemExit(f"No images under {cache_dir / split}.")
        self.tf = _train_tf() if augment else _eval_tf()

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return self.tf(torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1)), label

    def class_counts(self):
        counts = [0] * len(CLASSES)
        for _, label in self.samples:
            counts[label] += 1
        return counts


def _train_tf():
    # RandAugment needs uint8; geometric + RandAugment run first, then float+norm,
    # then RandomErasing on the normalized tensor.
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0), antialias=True),
        transforms.RandomHorizontalFlip(),
        transforms.RandAugment(num_ops=2, magnitude=7),
        transforms.ConvertImageDtype(torch.float),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.15)),
    ])


def _eval_tf():
    return transforms.Compose([
        transforms.Resize(256, antialias=True),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ConvertImageDtype(torch.float),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


# ---- model -------------------------------------------------------------------

def build_model(backbone):
    """Return a model with an unfrozen head + last few feature blocks."""
    if backbone == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        head_idx = 3
    elif backbone == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        head_idx = 1
    else:
        raise SystemExit(f"unknown backbone {backbone}")

    for p in model.parameters():
        p.requires_grad = False
    for block in model.features[-UNFREEZE_LAST_BLOCKS:]:
        for p in block.parameters():
            p.requires_grad = True
    in_features = model.classifier[head_idx].in_features
    model.classifier[head_idx] = nn.Linear(in_features, len(CLASSES))  # fresh, trainable
    return model


def param_groups(model, lr_head, lr_backbone):
    head, backbone = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        (head if name.startswith("classifier") else backbone).append(p)
    return [{"params": head, "lr": lr_head}, {"params": backbone, "lr": lr_backbone}]


class EMA:
    """Exponential moving average of model params; evaluate/save the smoothed copy."""
    def __init__(self, model, decay):
        self.decay = decay
        self.shadow = {k: v.detach().clone() for k, v in model.state_dict().items()}

    def update(self, model):
        for k, v in model.state_dict().items():
            s = self.shadow[k]
            if v.dtype.is_floating_point:
                s.mul_(self.decay).add_(v.detach(), alpha=1 - self.decay)
            else:
                s.copy_(v)

    def copy_to(self, model):
        model.load_state_dict(self.shadow, strict=True)


# ---- mixup / cutmix ----------------------------------------------------------

def mix_batch(x, y):
    """Return (x, y_a, y_b, lam) applying MixUp or CutMix with prob MIX_PROB."""
    if random.random() > MIX_PROB:
        return x, y, y, 1.0
    lam = float(np.random.beta(MIX_ALPHA, MIX_ALPHA))
    perm = torch.randperm(x.size(0))
    if random.random() < 0.5:  # mixup
        x = lam * x + (1 - lam) * x[perm]
    else:                      # cutmix
        _, _, h, w = x.shape
        rh, rw = int(h * np.sqrt(1 - lam)), int(w * np.sqrt(1 - lam))
        cy, cx = np.random.randint(h), np.random.randint(w)
        y1, y2 = np.clip([cy - rh // 2, cy + rh // 2], 0, h)
        x1, x2 = np.clip([cx - rw // 2, cx + rw // 2], 0, w)
        x[:, :, y1:y2, x1:x2] = x[perm, :, y1:y2, x1:x2]
        lam = 1 - ((x2 - x1) * (y2 - y1) / (h * w))
    return x, y, y[perm], lam


# ---- train / eval loops ------------------------------------------------------

def train_epoch(model, loader, criterion, optimizer, scheduler, ema, device):
    model.train()
    loss_sum, total = 0.0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        x, ya, yb, lam = mix_batch(x, y)
        out = model(x)
        loss = lam * criterion(out, ya) + (1 - lam) * criterion(out, yb)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        ema.update(model)
        loss_sum += loss.item() * x.size(0)
        total += x.size(0)
    scheduler.step()
    return loss_sum / total


@torch.no_grad()
def eval_acc(model, loader, device):
    model.eval()
    correct, total = 0, 0
    for x, y in loader:
        pred = model(x.to(device)).argmax(1).cpu()
        correct += (pred == y).sum().item()
        total += x.size(0)
    return correct / total


@torch.no_grad()
def collect_logits(model, loader, device):
    model.eval()
    logits, ys = [], []
    for x, y in loader:
        logits.append(model(x.to(device)).cpu())
        ys.append(y)
    return torch.cat(logits), torch.cat(ys)


def fit_temperature(logits, y):
    log_t = torch.zeros(1, requires_grad=True)
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
        prec = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
        rec = tp / cm[i].sum() if cm[i].sum() else 0.0
        flag = "  <- condition recall" if c != "healthy" else ""
        print(f"  {c:12s} P {prec:.3f}  R {rec:.3f}  (n={cm[i].sum()}){flag}")
    acc = np.trace(cm) / cm.sum()
    print(f"\noverall test accuracy {acc:.3f}")
    return acc


def register_member(backbone, weights_file, temperature, img_size):
    """Add/replace this backbone in the ensemble manifest (labels json)."""
    MODELS.mkdir(parents=True, exist_ok=True)
    meta = json.loads(LABELS_JSON.read_text()) if LABELS_JSON.exists() else {}
    meta.update({"classes": CLASSES, "img_size": img_size,
                 "mean": IMAGENET_MEAN, "std": IMAGENET_STD})
    members = [m for m in meta.get("ensemble", []) if m["backbone"] != backbone]
    members.append({"backbone": backbone, "weights_file": weights_file,
                    "temperature": round(temperature, 4)})
    meta["ensemble"] = members
    LABELS_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"ensemble now: {[m['backbone'] for m in members]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone", default="mobilenet_v3_large",
                    choices=["mobilenet_v3_large", "efficientnet_b0"])
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr-head", type=float, default=1e-3)
    ap.add_argument("--lr-backbone", type=float, default=1e-4)
    args = ap.parse_args()

    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_dir = Path(args.data_dir) if args.data_dir else _default_data_dir()
    print(f"Device: {device} | backbone: {args.backbone} | data: {data_dir.name} | classes: {CLASSES}")

    cache = ensure_roi_cache(data_dir)
    train_ds = NailDataset(cache, "train", augment=True)
    valid_ds = NailDataset(cache, "valid", augment=False)
    test_ds = NailDataset(cache, "test", augment=False)
    print(f"Sizes -> train {len(train_ds)}, valid {len(valid_ds)}, test {len(test_ds)}")

    train_dl = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0)
    valid_dl = DataLoader(valid_ds, batch_size=BATCH, num_workers=0)
    test_dl = DataLoader(test_ds, batch_size=BATCH, num_workers=0)

    counts = torch.tensor(train_ds.class_counts(), dtype=torch.float)
    weights = (counts.sum() / (len(CLASSES) * counts)).to(device)
    print(f"train class counts {counts.int().tolist()} | weights {[round(w,3) for w in weights.tolist()]}")

    model = build_model(args.backbone).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(
        param_groups(model, args.lr_head, args.lr_backbone), weight_decay=WEIGHT_DECAY)
    warmup = torch.optim.lr_scheduler.LinearLR(
        optimizer, start_factor=0.1, total_iters=WARMUP_EPOCHS)
    cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, args.epochs - WARMUP_EPOCHS))
    scheduler = torch.optim.lr_scheduler.SequentialLR(
        optimizer, [warmup, cosine], milestones=[WARMUP_EPOCHS])
    ema = EMA(model, EMA_DECAY)

    best_acc, best_shadow, since = 0.0, None, 0
    for epoch in range(1, args.epochs + 1):
        tr_loss = train_epoch(model, train_dl, criterion, optimizer, scheduler, ema, device)
        ema_model = build_model(args.backbone).to(device)
        ema.copy_to(ema_model)
        va = eval_acc(ema_model, valid_dl, device)
        print(f"epoch {epoch:2d}  train_loss {tr_loss:.3f}  val_acc(ema) {va:.3f}")
        if va >= best_acc:
            best_acc, best_shadow, since = va, {k: v.clone() for k, v in ema.shadow.items()}, 0
        else:
            since += 1
            if since >= PATIENCE:
                print(f"early stop (no val improvement in {PATIENCE} epochs)")
                break

    best = build_model(args.backbone).to(device)
    best.load_state_dict(best_shadow, strict=True)

    valid_logits, valid_y = collect_logits(best, valid_dl, device)
    temperature = fit_temperature(valid_logits, valid_y)
    print(f"\nBest val_acc {best_acc:.3f} | temperature {temperature:.3f}")
    test_logits, test_y = collect_logits(best, test_dl, device)
    report(test_logits, test_y, temperature)

    weights_file = f"nail_classifier__{args.backbone}.pt"
    torch.save(best.state_dict(), MODELS / weights_file)
    register_member(args.backbone, weights_file, temperature, IMG_SIZE)
    print(f"Saved -> {MODELS / weights_file}")


if __name__ == "__main__":
    main()
