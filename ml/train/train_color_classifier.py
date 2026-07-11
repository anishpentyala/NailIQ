"""Transfer-learn the COLOR-condition classifier, ensemble-ready.

Sibling of ml/train/train_classifier.py (the geometry-condition CNN). Same recipe --
partial fine-tune, RandAugment + MixUp/CutMix, EMA, cosine LR, temperature scaling --
but a different job: it classifies a nail-PLATE crop into one of KNM's colour/texture
classes, to give the classical colour heuristics (cyanosis.py, terrys_nails.py, ...) a
data-backed second opinion. Most of those heuristics calibrated near chance on real
photos (see ml/eval/calibrate_color.py); a CNN trained on the same labels does better.

    cd <repo root>
    backend/venv/Scripts/python.exe scripts/build_color_classification_dataset.py
    backend/venv/Scripts/python.exe ml/train/train_color_classifier.py --backbone mobilenet_v3_large
    backend/venv/Scripts/python.exe ml/train/train_color_classifier.py --backbone efficientnet_b0

Data: data/raw/color_cls/{train,valid,test}/<slug>/ from the build script above
(KNM box crops, CC BY 4.0). Classes are discovered from the train folders.

Two deliberate differences from train_classifier.py:
  - NO ROI re-crop. The geometry trainer caches a crop_to_finger_roi pass so the CNN
    sees the nail not the background; here the inputs are ALREADY tight nail-plate
    crops, and running the finger detector on them would mangle them (no silhouette).
  - Separate manifest + weights (nail_color_classifier_labels.json /
    nail_color_classifier__<backbone>.pt) so this ensemble is independent of the
    geometry one.

HONESTY NOTE: accuracy printed here is on KNM's held-out split -- clinical photos,
not real phone photos. Treat real-world accuracy as unknown/lower, exactly as for the
geometry CNN. Never present any of these as a diagnosis.
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
from torchvision import models

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
MODELS = REPO / "ml" / "models"
LABELS_JSON = MODELS / "nail_color_classifier_labels.json"
DATA_DIR = REPO / "data" / "raw" / "color_cls"

# Reuse the geometry trainer's generic (class-count-independent) machinery so the two
# stay in lockstep -- only the class set, data layout, and manifest differ here.
from ml.train.train_classifier import (  # noqa: E402
    BATCH, EMA, IMAGENET_MEAN, IMAGENET_STD, IMG_SIZE, LABEL_SMOOTHING,
    PATIENCE, SEED, UNFREEZE_LAST_BLOCKS, WARMUP_EPOCHS, WEIGHT_DECAY,
    _eval_tf, _train_tf, collect_logits, eval_acc, fit_temperature,
    param_groups, train_epoch,
)

_EXTS = {".jpg", ".jpeg", ".png"}

# Of the trained classes, the ones the app actually screens for in the colour track.
# (clubbing/koilonychia belong to the geometry track; melanoma/onychogryphosis aren't
# app findings -- all three are kept as classes only so the model can tell them apart.)
# Presence of a class here is a no-op until its data is on disk -- discover_classes()
# decides what actually trains. `pallor` needs the Ghana fingernail-anemia set;
# leukonychia/onycholysis/splinter_hemorrhages/lindsays_nails need the nail-disease set;
# `melanonychia` needs the arthitaya set (all via
# scripts/build_color_classification_dataset.py). These were added to give previously
# heuristic-only conditions -- which false-positived on healthy nails (leukonychia
# ~61%) or, for melanonychia, had NO training data anywhere -- a CNN color_fusion.py
# can make primary over the heuristic. With melanonychia's addition, every condition
# the app screens for now has (or will have, once trained) a CNN behind it.
APP_CONDITIONS = ["cyanosis", "terrys_nails", "beaus_lines", "muehrckes_lines", "pitting",
                  "pallor", "leukonychia", "onycholysis", "splinter_hemorrhages",
                  "lindsays_nails", "melanonychia"]


def discover_classes():
    train = DATA_DIR / "train"
    if not train.is_dir():
        raise SystemExit(f"No dataset at {train} -- run scripts/build_color_classification_dataset.py.")
    return sorted(d.name for d in train.iterdir() if d.is_dir())


class CropDataset(Dataset):
    """Reads <DATA_DIR>/<split>/<class>/*.jpg directly (crops are already nail plates)."""

    def __init__(self, classes, split, augment):
        self.classes = classes
        self.label_to_idx = {c: i for i, c in enumerate(classes)}
        self.samples = []
        for cls in classes:
            d = DATA_DIR / split / cls
            if not d.is_dir():
                continue
            for p in d.iterdir():
                if p.suffix.lower() in _EXTS:
                    self.samples.append((p, self.label_to_idx[cls]))
        if not self.samples:
            raise SystemExit(f"No images under {DATA_DIR / split}.")
        self.tf = _train_tf() if augment else _eval_tf()

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return self.tf(torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1)), label

    def class_counts(self):
        counts = [0] * len(self.classes)
        for _, label in self.samples:
            counts[label] += 1
        return counts


def build_model(backbone, num_classes):
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
    model.classifier[head_idx] = nn.Linear(in_features, num_classes)
    return model


def report(classes, logits, y, temperature):
    """Confusion matrix + per-class P/R, flagging recall on the app's colour conditions."""
    n = len(classes)
    preds = (logits / temperature).argmax(1)
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y.tolist(), preds.tolist()):
        cm[t][p] += 1
    print("\nper-class precision / recall:")
    for i, c in enumerate(classes):
        tp = cm[i][i]
        prec = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
        rec = tp / cm[i].sum() if cm[i].sum() else 0.0
        flag = "  <- app condition recall" if c in APP_CONDITIONS else ""
        print(f"  {c:16s} P {prec:.3f}  R {rec:.3f}  (n={cm[i].sum()}){flag}")
    acc = np.trace(cm) / cm.sum()
    # The number that matters for the app is accuracy *restricted to* the classes it
    # reports plus healthy -- the rest are discrimination-only.
    app_idx = [i for i, c in enumerate(classes) if c in APP_CONDITIONS or c == "healthy"]
    app_mask = np.isin(y.numpy(), app_idx)
    app_acc = (preds.numpy()[app_mask] == y.numpy()[app_mask]).mean() if app_mask.any() else 0.0
    print(f"\noverall test accuracy {acc:.3f} (all {n} classes)")
    print(f"accuracy on app conditions + healthy {app_acc:.3f} (n={int(app_mask.sum())})")
    return acc


def register_member(classes, backbone, weights_file, temperature):
    MODELS.mkdir(parents=True, exist_ok=True)
    meta = json.loads(LABELS_JSON.read_text()) if LABELS_JSON.exists() else {}
    meta.update({"classes": classes, "img_size": IMG_SIZE,
                 "mean": IMAGENET_MEAN, "std": IMAGENET_STD,
                 "app_conditions": APP_CONDITIONS})
    members = [m for m in meta.get("ensemble", []) if m["backbone"] != backbone]
    members.append({"backbone": backbone, "weights_file": weights_file,
                    "temperature": round(temperature, 4)})
    meta["ensemble"] = members
    LABELS_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"colour ensemble now: {[m['backbone'] for m in members]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone", default="mobilenet_v3_large",
                    choices=["mobilenet_v3_large", "efficientnet_b0"])
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr-head", type=float, default=1e-3)
    ap.add_argument("--lr-backbone", type=float, default=1e-4)
    args = ap.parse_args()

    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    classes = discover_classes()
    print(f"Device: {device} | backbone: {args.backbone} | classes ({len(classes)}): {classes}")

    train_ds = CropDataset(classes, "train", augment=True)
    valid_ds = CropDataset(classes, "valid", augment=False)
    test_ds = CropDataset(classes, "test", augment=False)
    print(f"Sizes -> train {len(train_ds)}, valid {len(valid_ds)}, test {len(test_ds)}")

    train_dl = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0)
    valid_dl = DataLoader(valid_ds, batch_size=BATCH, num_workers=0)
    test_dl = DataLoader(test_ds, batch_size=BATCH, num_workers=0)

    counts = torch.tensor(train_ds.class_counts(), dtype=torch.float)
    # Sqrt-dampened inverse frequency, not raw inverse frequency: with 17 classes now
    # (melanonychia n=51, mees_lines n=48 are the newest, smallest), raw inverse-freq
    # weighting over-corrects for them and starves gradient signal from the larger,
    # already-hard-to-calibrate classes (leukonychia, pitting, pallor), which is what
    # caused those classes' real-photo false-positive rate to regress when melanonychia
    # was added (see fp_rate.py results in this session). Sqrt keeps rare classes
    # up-weighted without letting them dominate the loss.
    weights = (counts.sum() / (len(classes) * counts)).sqrt().to(device)
    print(f"train class counts {counts.int().tolist()}")

    model = build_model(args.backbone, len(classes)).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(
        param_groups(model, args.lr_head, args.lr_backbone), weight_decay=WEIGHT_DECAY)
    warmup = torch.optim.lr_scheduler.LinearLR(
        optimizer, start_factor=0.1, total_iters=WARMUP_EPOCHS)
    cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, args.epochs - WARMUP_EPOCHS))
    scheduler = torch.optim.lr_scheduler.SequentialLR(
        optimizer, [warmup, cosine], milestones=[WARMUP_EPOCHS])
    ema = EMA(model, 0.999)

    best_acc, best_shadow, since = 0.0, None, 0
    for epoch in range(1, args.epochs + 1):
        tr_loss = train_epoch(model, train_dl, criterion, optimizer, scheduler, ema, device)
        ema_model = build_model(args.backbone, len(classes)).to(device)
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

    best = build_model(args.backbone, len(classes)).to(device)
    best.load_state_dict(best_shadow, strict=True)

    valid_logits, valid_y = collect_logits(best, valid_dl, device)
    temperature = fit_temperature(valid_logits, valid_y)
    print(f"\nBest val_acc {best_acc:.3f} | temperature {temperature:.3f}")
    test_logits, test_y = collect_logits(best, test_dl, device)
    report(classes, test_logits, test_y, temperature)

    weights_file = f"nail_color_classifier__{args.backbone}.pt"
    torch.save(best.state_dict(), MODELS / weights_file)
    register_member(classes, args.backbone, weights_file, temperature)
    print(f"Saved -> {MODELS / weights_file}")


if __name__ == "__main__":
    main()
