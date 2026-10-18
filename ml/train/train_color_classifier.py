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
import hashlib
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
LABELS_JSON = MODELS / "nail_color_classifier_labels.json"
DATA_DIR = REPO / "data" / "raw" / "color_cls"

# Reuse the geometry trainer's generic (class-count-independent) machinery so the two
# stay in lockstep -- only the class set, data layout, and manifest differ here.
from ml.train.train_classifier import (  # noqa: E402
    BATCH, EMA, IMAGENET_MEAN, IMAGENET_STD, IMG_SIZE, LABEL_SMOOTHING,
    PATIENCE, SEED, UNFREEZE_LAST_BLOCKS, WARMUP_EPOCHS, WEIGHT_DECAY,
    _eval_tf, collect_logits, eval_acc, fit_temperature,
    param_groups, train_epoch,
)
from ml.train.model_average import WarmupEMA

_EXTS = {".jpg", ".jpeg", ".png"}


def _train_tf_color():
    """TRIED AND REVERTED: this used to override RandomResizedCrop's scale to
    (0.85, 1.0) (vs. the geometry trainer's (0.6, 1.0)), on the theory that
    onycholysis/lindsays_nails/muehrckes_lines/beaus_lines/leukonychia - which are
    confused with EACH OTHER far more than clean test-set numbers suggest (see
    ml/eval/eval_color_sensitivity.py's per-finding CNN output; a true onycholysis
    photo was once confidently called muehrckes_lines at 0.87) - were losing their
    distinguishing pattern (a groove vs. a band vs. a patch vs. edge separation) to
    aggressive cropping on an already-tight nail-plate crop.

    Tested via a full retrain + ensemble eval + `eval_color_sensitivity.py` +
    `fp_rate`-style false-positive check: it was a clear regression, not a fix.
    Pallor's end-to-end recall (a real, hard-won win from a confidence-threshold fix
    earlier this session) crashed 76.2% -> 47.7%; onycholysis's own end-to-end
    recall got WORSE (19.0% -> 9.5%); false-positive rates rose broadly (leukonychia
    13.2% -> 20.2%, splinter_hemorrhages 7.9% -> 9.6%, cyanosis 3.5% -> 6.1%).
    Reducing crop-augmentation diversity apparently hurt generalization more than it
    helped fine-grained discrimination. Reverted to match `_train_tf` exactly.
    Left as its own function (not just calling `_train_tf` from train_classifier.py)
    so the next person who has this same idea can see it was already tried, and
    isn't tempted to reach for a smaller scale range as a first move - if you retry
    this, it needs a different angle (e.g. higher resolution instead of less
    cropping, or actually building the hierarchical classifier for this cluster)
    to have a real chance.
    """
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0), antialias=True),
        transforms.RandomHorizontalFlip(),
        transforms.RandAugment(num_ops=2, magnitude=7),
        transforms.ConvertImageDtype(torch.float),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.15)),
    ])

# Of the trained classes, the ones the app actually screens for in the colour track.
# (clubbing/koilonychia belong to the geometry track; melanoma isn't an app finding --
# kept as a class only so the model can tell it apart. onychogryphosis became an
# AI-only app finding 2026-09, see ml/infer/onychogryphosis.py.)
# Presence of a class here is a no-op until its data is on disk -- discover_classes()
# decides what actually trains. `pallor` needs the Ghana fingernail-anemia set;
# leukonychia/onycholysis/splinter_hemorrhages/lindsays_nails need the nail-disease set
# (all via scripts/build_color_classification_dataset.py). These were added to give
# previously heuristic-only conditions -- which false-positived on healthy nails
# (leukonychia ~61%) -- a CNN color_fusion.py can make primary over the heuristic.
# Arthitaya is authorized by the user as of 2026-10-01. Its labels can train a
# candidate; tiny held-out counts do not establish a validated finding.
APP_CONDITIONS = ["cyanosis", "terrys_nails", "beaus_lines", "muehrckes_lines", "pitting",
                  "pallor", "leukonychia", "onycholysis", "splinter_hemorrhages",
                  "lindsays_nails", "onychogryphosis", "melanonychia"]


def discover_classes():
    train = DATA_DIR / "train"
    if not train.is_dir():
        raise SystemExit(f"No dataset at {train} -- run scripts/build_color_classification_dataset.py.")
    return sorted(d.name for d in train.iterdir() if d.is_dir())


class CropDataset(Dataset):
    """Reads <DATA_DIR>/<split>/<class>/*.jpg directly (crops are already nail plates)."""

    def __init__(self, classes, split, augment, exclusions=None, data_root=None):
        data_root = Path(data_root) if data_root is not None else DATA_DIR
        self.classes = classes
        self.label_to_idx = {c: i for i, c in enumerate(classes)}
        self.samples = []
        excluded = set((exclusions or {}).get("excluded_crops", []))
        for cls in classes:
            d = data_root / split / cls
            if not d.is_dir():
                continue
            for p in d.iterdir():
                if p.suffix.lower() in _EXTS and p.relative_to(data_root).as_posix() not in excluded:
                    self.samples.append((p, self.label_to_idx[cls]))
        if not self.samples:
            raise SystemExit(f"No images under {data_root / split}.")
        self.tf = _train_tf_color() if augment else _eval_tf()

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


def initialize_candidate(model, classes, backbone, directory):
    """Transfer compatible weights, aligning classifier rows by label name."""
    manifest = json.loads((directory / 'nail_color_classifier_labels.json').read_text())
    member = next((m for m in manifest.get('ensemble', []) if m['backbone'] == backbone), None)
    if member is None:
        raise SystemExit('Initialization candidate does not contain the requested backbone')
    weights_path = directory / member['weights_file']
    source = torch.load(weights_path, map_location='cpu', weights_only=True)
    target = model.state_dict()
    head = 'classifier.3' if backbone == 'mobilenet_v3_large' else 'classifier.1'
    for key in target:
        if key.startswith(head + '.'):
            continue
        if key not in source or target[key].shape != source[key].shape:
            raise SystemExit(f'Initialization architecture differs at {key}')
        target[key] = source[key]
    for index, label in enumerate(classes):
        if label in manifest['classes']:
            old_index = manifest['classes'].index(label)
            for suffix in ('weight', 'bias'):
                target[f'{head}.{suffix}'][index] = source[f'{head}.{suffix}'][old_index]
    model.load_state_dict(target)
    return {'directory': str(directory.resolve()), 'classes': manifest['classes'],
            'weights_sha256': hashlib.sha256(weights_path.read_bytes()).hexdigest()}


def initialize_worker(_):
    torch.set_num_threads(1)
    cv2.setNumThreads(1)
    random.seed(torch.initial_seed() % (2 ** 32))
    np.random.seed(torch.initial_seed() % (2 ** 32))


def fit_color_temperature(logits, targets):
    """Bounded calibration, including the same two-view average used at inference."""
    if logits.ndim not in (2, 3) or not torch.isfinite(logits).all() or len(logits) != len(targets) or not len(targets):
        raise ValueError('Finite nonempty calibration logits and matching targets required')
    values = torch.cat((torch.logspace(np.log10(.05), np.log10(100.), 401), torch.ones(1)))
    losses = []
    with torch.no_grad():
        for value in values:
            if logits.ndim == 3:
                probabilities = torch.softmax(logits / value, -1).mean(1)
                loss = nn.functional.nll_loss(probabilities.clamp_min(1e-12).log(), targets)
            else:
                loss = nn.functional.cross_entropy(logits / value, targets)
            losses.append(float(loss))
    if not np.isfinite(losses).all():
        raise ValueError('Nonfinite temperature objective')
    return float(values[int(np.argmin(losses))])


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
                 "app_conditions": [c for c in APP_CONDITIONS if c in classes]})
    meta["appearance_conditions"] = [c for c in ("clubbing", "koilonychia") if c in classes]
    members = [m for m in meta.get("ensemble", []) if m["backbone"] != backbone]
    members.append({"backbone": backbone, "weights_file": weights_file,
                    "temperature": round(temperature, 4)})
    meta["ensemble"] = members
    LABELS_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"colour ensemble now: {[m['backbone'] for m in members]}")


def main():
    global DATA_DIR, MODELS, LABELS_JSON
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone", default="mobilenet_v3_large",
                    choices=["mobilenet_v3_large", "efficientnet_b0"])
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument('--ema-mode', choices=('warmup', 'legacy'), default='warmup')
    ap.add_argument("--batch-size", type=int, default=BATCH)
    ap.add_argument('--condition', choices=APP_CONDITIONS + ['clubbing', 'koilonychia'])
    ap.add_argument('--source-matched', action='store_true', help='Use only TRAIN sources providing both target and healthy labels')
    ap.add_argument('--initialize-from', type=Path, help='Transfer an earlier candidate, aligning head rows by label')
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--checkpoint-every-epoch', action='store_true')
    ap.add_argument("--lr-head", type=float, default=1e-3)
    ap.add_argument("--lr-backbone", type=float, default=1e-4)
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--output-dir", type=Path, default=MODELS)
    ap.add_argument("--exclusions", type=Path)
    ap.add_argument("--extra-train-dir", type=Path,
                    help="Completed runtime-crop experiment: append its TRAIN crops only")
    ap.add_argument("--validation-dir", type=Path,
                    help="Completed runtime-crop experiment used for checkpoint selection; endpoint evaluation still required")
    ap.add_argument("--selection", choices=["accuracy", "macro_recall"], default="accuracy")
    ap.add_argument("--evaluate-test", action="store_true",
                    help="Explicit final evaluation only; experiments select on validation")
    args = ap.parse_args()
    if args.workers < 0:
        ap.error('--workers cannot be negative')
    if args.batch_size < 1:
        ap.error("--batch-size must be positive")
    if args.epochs < 1 or not 0 <= args.seed < 2**32:
        ap.error('Positive epochs and a seed between 0 and 2**32-1 required')
    DATA_DIR, MODELS = args.data_dir.resolve(), args.output_dir.resolve()
    LABELS_JSON = MODELS / "nail_color_classifier_labels.json"
    MODELS.mkdir(parents=True, exist_ok=True)
    exclusions = json.loads(args.exclusions.read_text()) if args.exclusions else None
    runtime_manifests = {}
    for directory in (args.extra_train_dir, args.validation_dir):
        if directory is None:
            continue
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise SystemExit(f"Runtime crop build is incomplete: {directory}")
        manifest = json.loads(manifest_path.read_text())
        exclusion_hash = hashlib.sha256(args.exclusions.read_bytes()).hexdigest() if args.exclusions else None
        if manifest.get("exclusions_sha256") != exclusion_hash:
            raise SystemExit("Runtime crops and training must use the same exclusion manifest")
        if any(row["split"] not in {"train", "valid"} for row in manifest["rows"]):
            raise SystemExit("Runtime experiment contains unexpected split data")
        runtime_manifests[str(directory.resolve())] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    classes = discover_classes()
    if args.condition:
        if args.condition not in classes or 'healthy' not in classes:
            raise SystemExit('Specialist requires target and healthy training classes')
        classes = sorted(['healthy', args.condition])
    print(f"Device: {device} | backbone: {args.backbone} | classes ({len(classes)}): {classes}")

    train_ds = CropDataset(classes, "train", augment=True, exclusions=exclusions)
    if args.extra_train_dir:
        extra = CropDataset(classes, "train", augment=True, data_root=args.extra_train_dir)
        train_ds.samples.extend(extra.samples)
        print(f"Appended {len(extra)} production-localized TRAIN crops (not new independent subjects)")
    valid_ds = CropDataset(classes, "valid", augment=False,
                           exclusions=None if args.validation_dir else exclusions,
                           data_root=args.validation_dir)
    matched_sources = None
    if args.source_matched:
        if not args.condition or args.extra_train_dir:
            raise SystemExit('--source-matched requires --condition and original provenance-named crops')
        sources = [{path.name.split('__', 1)[0] for path, label in train_ds.samples if label == i}
                   for i in range(len(classes))]
        matched_sources = sorted(set.intersection(*sources))
        if not matched_sources:
            raise SystemExit('No source provides both target and healthy training examples')
        for dataset in (train_ds, valid_ds):
            dataset.samples = [(path, label) for path, label in dataset.samples
                               if path.name.split('__', 1)[0] in matched_sources]
        if any(count == 0 for count in train_ds.class_counts()) or any(count == 0 for count in valid_ds.class_counts()):
            raise SystemExit('Matched sources lack both classes on TRAIN or VALID')
    print(f"Sizes -> train {len(train_ds)}, valid {len(valid_ds)}; selection={args.selection}")

    loader_options = {'num_workers': args.workers, 'pin_memory': device.type == 'cuda',
                      'persistent_workers': args.workers > 0, 'worker_init_fn': initialize_worker}
    train_dl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, **loader_options)
    valid_dl = DataLoader(valid_ds, batch_size=args.batch_size, **loader_options)

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
    initialization = initialize_candidate(model, classes, args.backbone, args.initialize_from) if args.initialize_from else None
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(
        param_groups(model, args.lr_head, args.lr_backbone), weight_decay=WEIGHT_DECAY)
    warmup = torch.optim.lr_scheduler.LinearLR(
        optimizer, start_factor=0.1, total_iters=WARMUP_EPOCHS)
    cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, args.epochs - WARMUP_EPOCHS))
    scheduler = torch.optim.lr_scheduler.SequentialLR(
        optimizer, [warmup, cosine], milestones=[WARMUP_EPOCHS])
    ema = (WarmupEMA if args.ema_mode == 'warmup' else EMA)(model, 0.999)

    best_acc, best_shadow, since = 0.0, None, 0
    best_epoch, best_updates = 0, 0
    history = []
    for epoch in range(1, args.epochs + 1):
        tr_loss = train_epoch(model, train_dl, criterion, optimizer, scheduler, ema, device)
        ema_model = build_model(args.backbone, len(classes)).to(device)
        ema.copy_to(ema_model)
        if args.selection == "macro_recall":
            logits, targets = collect_logits(ema_model, valid_dl, device)
            predictions = logits.argmax(1)
            recalls = [(predictions[targets == i] == i).float().mean().item()
                       for i, label in enumerate(classes)
                       if (label in APP_CONDITIONS or label in {"healthy", "clubbing", "koilonychia"}) and (targets == i).any()]
            va = sum(recalls) / len(recalls)
        else:
            va = eval_acc(ema_model, valid_dl, device)
        print(f"epoch {epoch:2d}  train_loss {tr_loss:.3f}  valid_{args.selection}(ema) {va:.3f}")
        updates = epoch * len(train_dl)
        initial_weight = ema.initial_weight if args.ema_mode == 'warmup' else .999 ** updates
        history.append({'epoch': epoch, 'train_loss': tr_loss, 'valid_score': va,
                        'updates': updates, 'initialization_weight': initial_weight})
        if va >= best_acc:
            best_acc, best_shadow, since = va, {k: v.clone() for k, v in ema.shadow.items()}, 0
            best_epoch, best_updates = epoch, updates
            if args.checkpoint_every_epoch:
                torch.save({key: value.cpu() for key, value in best_shadow.items()},
                           MODELS / f'checkpoint_{args.backbone}.pt')
        else:
            since += 1
            if since >= PATIENCE:
                print(f"early stop (no val improvement in {PATIENCE} epochs)")
                break
        if args.checkpoint_every_epoch:
            progress = {'epoch': epoch, 'current_valid_score': va, 'best_valid_score': best_acc,
                        'scope': 'TRAIN/VALID crop experiment only; not an endpoint or TEST result'}
            if args.selection == 'macro_recall':
                progress['valid_class_recalls'] = {label: float((predictions[targets == i] == i).float().mean())
                    for i, label in enumerate(classes) if (targets == i).any()}
            (MODELS / f'progress_{args.backbone}.json').write_text(json.dumps(progress, indent=2))

    best = build_model(args.backbone, len(classes)).to(device)
    best.load_state_dict(best_shadow, strict=True)

    valid_logits, valid_y = collect_logits(best, valid_dl, device)
    temperature = fit_color_temperature(valid_logits, valid_y)
    print(f"\nBest valid_{args.selection} {best_acc:.3f} | temperature {temperature:.3f}")
    if args.evaluate_test:
        test_ds = CropDataset(classes, "test", augment=False, exclusions=exclusions)
        test_dl = DataLoader(test_ds, batch_size=args.batch_size, num_workers=0)
        test_logits, test_y = collect_logits(best, test_dl, device)
        report(classes, test_logits, test_y, temperature)

    weights_file = f"nail_color_classifier__{args.backbone}.pt"
    torch.save(best.state_dict(), MODELS / weights_file)
    register_member(classes, args.backbone, weights_file, temperature)
    (MODELS / f"training_{args.backbone}.json").write_text(json.dumps({
        "data_dir": str(DATA_DIR), "selection": args.selection,
        "best_valid_score": best_acc, "seed": args.seed, "epochs_run": epoch,
        'best_epoch': best_epoch, 'best_updates': best_updates,
        'ema_mode': args.ema_mode, 'ema_decay_ceiling': .999,
        'best_initialization_weight': 0.0 if args.ema_mode == 'warmup' else .999 ** best_updates,
        'history': history,
        "batch_size": args.batch_size,
        'condition': args.condition, 'matched_sources': matched_sources,
        'initialization': initialization,
        'workers': args.workers,
        "test_evaluated": args.evaluate_test, "classes": classes,
        "exclusions_sha256": hashlib.sha256(args.exclusions.read_bytes()).hexdigest() if args.exclusions else None,
        "runtime_manifests": runtime_manifests,
        "validation_dir": str(args.validation_dir.resolve()) if args.validation_dir else str(DATA_DIR),
    }, indent=2))
    print(f"Saved -> {MODELS / weights_file}")


if __name__ == "__main__":
    main()
