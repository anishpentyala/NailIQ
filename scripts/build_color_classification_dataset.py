"""Build data/raw/color_cls/{train,valid,test}/<slug>/ -- nail-plate crops for the
color-condition CNN (ml/train/train_color_classifier.py).

Sources (all Roboflow Universe, CC BY 4.0, YOLO detection format), merged by slug:
  1. data/raw/nail-disease-detection-mxoqy (KNM, 11 classes) -- kept in its OWN clean
     image-level train/valid/test split (no reshuffle, no leakage).
  2. data/raw/nail-disease (25 classes) -- supplies the four conditions that had no CNN
     backing and false-positived as pure heuristics (leukonychia, onycholysis,
     splinter_hemorrhages, lindsays_nails), plus extra examples for existing classes.
     Its shipped split is unusable (~all boxes of these classes are in `train`), so it
     is RE-SPLIT by image stem (leakage-safe: every box of one image goes to one split).
  3. data/raw/fingernails-ghana-anemia -- pallor / darker-cohort healthy (see below).
Each labeled box is cropped (with a small pad) to the nail plate and written as one
classification sample.

Why box crops, not full images (the opposite of scripts/build_color_eval_set.py):
the color-eval set feeds the CLASSICAL pipeline (ml/infer/nail_region.py), which
needs a whole finger silhouette to PCA-localize the nail and rejects tight crops as
"finger cropped out of frame." A CNN has no such constraint -- it eats the raw
pixels -- so for it the tight nail-box crop is exactly right: it removes skin and
background so the model keys on the nail plate's colour/texture, which is the whole
signal for these conditions. At inference (ml/infer/color_classifier.py) the
counterpart crop is nail_region's detected nail bbox, so train/inference see
comparable nail-plate crops.

Class set: the union of the mapped slugs across sources. It deliberately includes
classes the app does NOT individually report (melanoma, onychogryphosis, clubbing,
koilonychia): keeping them as their own classes makes the classifier discriminate
rather than forcing, say, a melanoma nail into "pitting." The inference layer emits
findings only for the colour conditions the app screens; the extra classes exist
purely to keep those honest.

Usage (from repo root):
    backend/venv/Scripts/python.exe scripts/build_color_classification_dataset.py
"""

import hashlib
import re
import shutil
from pathlib import Path

import cv2
import yaml

REPO = Path(__file__).resolve().parent.parent
KNM = REPO / "data" / "raw" / "nail-disease-detection-mxoqy"
OUT = REPO / "data" / "raw" / "color_cls"

# Second source: the Ghana fingernail-anemia set (data/raw/fingernails-ghana-anemia),
# 4,260 nail-plate crops from a Sub-Saharan (predominantly darker-skinned) cohort,
# labelled anemic / non-anemic in the filename. ml/eval/audit_skin_tone.py showed the
# KNM/NailCheck data is heavily light-skin-skewed, and the app's `pallor` condition has
# no CNN backing at all -- this set fixes both at once: anemic nails -> a real `pallor`
# class, non-anemic -> darker-cohort `healthy` examples, broadening the model's tone
# exposure. These images are already tight nail crops (like the KNM box crops), so they
# drop straight into the same classifier dataset with no box step.
GHANA = REPO / "data" / "raw" / "fingernails-ghana-anemia" / "Fingernails"

# Third source: the nail-disease detection set (data/raw/nail-disease, Roboflow
# Universe, CC BY 4.0, YOLO detection, 25 classes). It carries labeled boxes for the
# four conditions that had NO CNN backing and so false-positived badly as pure
# heuristics (measured on healthy photos: leukonychia ~61%, onycholysis/splinter ~21%,
# plus lindsays_nails, whose KNM class was only 2 boxes). Folding it in makes those
# four CNN-covered app conditions, so color_fusion.py's CNN-primary rule can override
# the trigger-happy heuristic -- the same mechanism that gave cyanosis/beaus/muehrckes
# their ~0% false-positive rate. Its OWN train/valid/test split is unusable (nearly
# every box of these classes sits in `train`, valid/test hold only a few unrelated
# classes), so unlike KNM we IGNORE its split and re-split by image (see resplit=True).
NAIL_DISEASE = REPO / "data" / "raw" / "nail-disease"

SPLITS = ["train", "valid", "test"]
BOX_PAD_FRAC = 0.15        # pad each side of the box; a little nail-fold context helps
MIN_CROP_PX = 24           # drop slivers that carry no usable colour/texture signal

# KNM class name -> internal slug. Lindsay-s Nail is intentionally absent (2 boxes in
# KNM -- but nail-disease below supplies 176, so lindsays_nails becomes a real class).
# Slugs match the app's condition labels where one exists; the rest are
# discrimination-only classes (no app finding emitted for them).
CLASS_SLUGS = {
    "Acral Lentiginous Melanoma": "melanoma",   # discrimination only (not melanonychia)
    "Beaus Line": "beaus_lines",
    "Blue Finger": "cyanosis",
    "Clubbing": "clubbing",                      # discrimination only (geometry owns it)
    "Healthy Nail": "healthy",
    "Koilonychia": "koilonychia",               # discrimination only (geometry owns it)
    "Muehrckes Lines": "muehrckes_lines",
    "Onychogryphosis": "onychogryphosis",        # discrimination only (not an app finding)
    "Pitting": "pitting",
    "Terry-s Nail": "terrys_nails",
}

# nail-disease class name -> internal slug. The first four are the newly-covered app
# conditions this whole ingestion exists for; the rest either strengthen an existing
# class or stay discrimination-only. Classes with no clean slug mapping (Onychomycosis,
# Psoriasis, pale-nail, white-nail, yellow-nail, etc.) are intentionally dropped rather
# than risk confusing them with leukonychia/pallor/Terry's.
NAIL_DISEASE_SLUGS = {
    "Leukonychia": "leukonychia",                # NEW app condition (was heuristic-only)
    "Onycholysis": "onycholysis",                # NEW app condition (was heuristic-only)
    "Splinter-hemmorrage": "splinter_hemorrhages",  # NEW app condition (was heuristic-only)
    "Lindsays-nail": "lindsays_nails",           # NEW app condition (KNM had too few)
    "Normal-nail": "healthy",
    "Terrys-nail": "terrys_nails",
    "Muehrckes-Lines": "muehrckes_lines",
    "beaus-lines": "beaus_lines",
    "bluish-nail": "cyanosis",
    "Melanoma": "melanoma",                      # discrimination only
    "Koilonychia": "koilonychia",               # discrimination only
    "Onychogryphosis": "onychogryphosis",        # discrimination only
    "clubbing-nail": "clubbing",                 # discrimination only
}

# Fourth source: data/raw/nail-dataset-arthitaya (Kaggle, "nail dataset" by arthitaya,
# 540 folder-classified images), the ONLY dataset found anywhere (Kaggle + Roboflow
# Universe both searched) carrying melanonychia labels -- the one app color condition
# that had no CNN backing at all. Cited by Coşar Soğukkuyu & Ata (2023, PeerJ Computer
# Science 9:e1533) as their melanonychia/Beau's/clubbing classifier's training source.
# A second listing, nail-dataset2, is a verified byte-for-byte subset of this one and is
# deliberately NOT used (would just inflate counts with duplicate images).
#
# LICENSE CAVEAT (see data/raw/LICENSES.md): Kaggle shows this dataset's license as
# "Unknown", unlike every other source above (all CC BY 4.0). Used here for
# research/screener training only -- verify licensing before any public release,
# redistribution of weights trained on it, or commercial use.
ARTHITAYA = REPO / "data" / "raw" / "nail-dataset-arthitaya" / "Nail"

# "black line" is this dataset's name for melanonychia (matches the PeerJ paper's
# terminology). "white spot" is leukonychia punctata (visually confirmed: discrete
# white spots on the nail plate). "other" is an ambiguous catch-all and is dropped.
# "mees_ line" (Mees' lines -- transverse white bands from arsenic/heavy-metal
# exposure) is medically distinct from muehrckes_lines and NOT an app condition, so
# it's kept as its own discrimination-only class rather than merged into anything.
ARTHITAYA_SLUGS = {
    "black line": "melanonychia",     # NEW app condition (was heuristic-only, no data anywhere)
    "white spot": "leukonychia",
    "beau_s line": "beaus_lines",
    "terry_s nail": "terrys_nails",
    "onycholysis": "onycholysis",
    "clubbing": "clubbing",            # discrimination only (geometry owns it)
    "normal": "healthy",
    "mees_ line": "mees_lines",         # discrimination only (distinct from muehrckes_lines)
}


def load_names(root):
    return yaml.safe_load((root / "data.yaml").read_text())["names"]


def find_image_file(label_path):
    images_dir = label_path.parent.parent / "images"
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = images_dir / (label_path.stem + ext)
        if candidate.exists():
            return candidate
    return None


def crop_box(img, cx, cy, bw, bh):
    """YOLO-normalized box -> padded pixel crop, clamped to the image. None if degenerate."""
    h, w = img.shape[:2]
    half_w, half_h = bw * w * (0.5 + BOX_PAD_FRAC), bh * h * (0.5 + BOX_PAD_FRAC)
    x1 = max(0, int(cx * w - half_w))
    y1 = max(0, int(cy * h - half_h))
    x2 = min(w, int(cx * w + half_w))
    y2 = min(h, int(cy * h + half_h))
    if x2 - x1 < MIN_CROP_PX or y2 - y1 < MIN_CROP_PX:
        return None
    crop = img[y1:y2, x1:x2]
    return crop if crop.size else None


# --- Ghana fingernail-anemia ingestion --------------------------------------

# Filenames look like "Anemic-FN-007 (2).png", "Non-Anrmic-FN-204.png",
# "Anmeic-fn-12.png" -- anemic/non-anemic with assorted typos, a patient number,
# and an optional (n) repeat index. We map anemic -> pallor, non-anemic -> healthy.
_ANEMIC_TOKENS = ("anemic", "anmeic", "anrmic", "anemia")


def ghana_label(name):
    """Filename -> 'pallor' (anemic) | 'healthy' (non-anemic) | None (unparseable)."""
    s = name.lower()
    if s.startswith("non") or "non-" in s or "non " in s:
        return "healthy"
    if any(tok in s for tok in _ANEMIC_TOKENS):
        return "pallor"
    return None


def ghana_patient_key(name, label):
    """Group all photos of one finger so they never straddle a split (no leakage).
    Key = label + first integer in the name (the patient/finger id); the trailing
    (n) repeat index is ignored because it's never the first integer."""
    m = re.search(r"\d+", name)
    pid = m.group(0).lstrip("0") or "0" if m else "x"
    return f"{label}-{pid}"


def bucket_split(key):
    """Deterministic 80/10/10 train/valid/test from a grouping key (md5 so it's stable
    across runs, unlike Python's salted hash()). Everything sharing a key lands in one
    split -- a patient/finger id for Ghana, an image stem for a re-split detection set --
    so no group straddles splits."""
    bucket = int(hashlib.md5(key.encode()).hexdigest(), 16) % 10
    return "train" if bucket < 8 else "valid" if bucket == 8 else "test"


def ingest_yolo(root, class_slugs, prefix, totals, resplit=False):
    """Crop every mapped box in a YOLO detection dataset into OUT/<split>/<slug>/.

    resplit=False: keep the dataset's own train/valid/test split (KNM ships a clean one).
    resplit=True:  ignore the source split and re-split by image stem via bucket_split
                   (for nail-disease, whose shipped split dumps ~all data into train).
    """
    if not root.exists():
        print(f"  {prefix}: dataset not found at {root} -- skipping")
        return
    names = load_names(root)
    idx_to_slug = {i: class_slugs[n] for i, n in enumerate(names) if n in class_slugs}
    added = {s: 0 for s in SPLITS}
    for src_split in SPLITS:
        labels_dir = root / src_split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in labels_dir.glob("*.txt"):
            img = img_file = None
            split = bucket_split(label_file.stem) if resplit else src_split
            for li, line in enumerate(label_file.read_text().splitlines()):
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                slug = idx_to_slug.get(int(parts[0]))
                if slug is None:
                    continue
                if img is None:            # lazily load image only when a box is kept
                    img_file = find_image_file(label_file)
                    if img_file is None:
                        break
                    img = cv2.imread(str(img_file), cv2.IMREAD_COLOR)
                    if img is None:
                        break
                cx, cy, bw, bh = map(float, parts[1:])
                crop = crop_box(img, cx, cy, bw, bh)
                if crop is None:
                    continue
                dst_dir = OUT / split / slug
                dst_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(dst_dir / f"{prefix}__{label_file.stem}__b{li}.jpg"), crop)
                added[split] += 1
                totals[split] = totals.get(split, 0) + 1
    print(f"  {prefix}: +{added}")


def add_ghana(totals):
    if not GHANA.exists():
        print(f"  Ghana set not found at {GHANA} -- skipping (color CNN stays light-skin-skewed)")
        return
    added = {s: 0 for s in SPLITS}
    skipped = 0
    for img_path in sorted(GHANA.glob("*.png")):
        label = ghana_label(img_path.name)
        if label is None:
            skipped += 1
            continue
        img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img is None or min(img.shape[:2]) < MIN_CROP_PX:
            skipped += 1
            continue
        split = bucket_split(ghana_patient_key(img_path.name, label))
        dst_dir = OUT / split / label
        dst_dir.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"[^A-Za-z0-9]+", "_", img_path.stem)
        cv2.imwrite(str(dst_dir / f"ghana__{stem}.jpg"), img)
        added[split] += 1
        totals[split] = totals.get(split, 0) + 1
    print(f"  ghana: +{added}  (skipped {skipped})")


def add_arthitaya(totals):
    """Whole-image ingestion (already close-up nail crops, no box step needed).
    No patient/subject id is available in this dataset, so the split key is the
    filename itself -- fine here since, unlike Ghana, there's no risk of the same
    subject's repeat photos straddling train/valid/test."""
    if not ARTHITAYA.exists():
        print(f"  arthitaya set not found at {ARTHITAYA} -- skipping "
              f"(melanonychia stays heuristic-only, no data anywhere else)")
        return
    added = {s: 0 for s in SPLITS}
    skipped = 0
    for cls_dir in sorted(ARTHITAYA.iterdir()):
        if not cls_dir.is_dir():
            continue
        slug = ARTHITAYA_SLUGS.get(cls_dir.name)
        if slug is None:          # "other": ambiguous catch-all, dropped
            continue
        for img_path in sorted(cls_dir.iterdir()):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
            if img is None or min(img.shape[:2]) < MIN_CROP_PX:
                skipped += 1
                continue
            split = bucket_split(f"{cls_dir.name}-{img_path.stem}")
            dst_dir = OUT / split / slug
            dst_dir.mkdir(parents=True, exist_ok=True)
            stem = re.sub(r"[^A-Za-z0-9]+", "_", f"{cls_dir.name}_{img_path.stem}")
            cv2.imwrite(str(dst_dir / f"arthitaya__{stem}.jpg"), img)
            added[split] += 1
            totals[split] = totals.get(split, 0) + 1
    print(f"  arthitaya: +{added}  (skipped {skipped})")


def main():
    if not KNM.exists():
        raise SystemExit(f"KNM dataset not found at {KNM} -- run scripts/download_data.py first.")
    if OUT.exists():
        print(f"Removing existing {OUT}")
        shutil.rmtree(OUT)

    totals = {}
    print("Ingesting KNM box crops (keep source split)...")
    ingest_yolo(KNM, CLASS_SLUGS, "knm", totals, resplit=False)
    print("Ingesting nail-disease box crops (re-split by image; adds leukonychia, "
          "onycholysis, splinter_hemorrhages, lindsays_nails)...")
    ingest_yolo(NAIL_DISEASE, NAIL_DISEASE_SLUGS, "nd", totals, resplit=True)
    print("Adding Ghana fingernail-anemia crops (pallor / darker-cohort healthy)...")
    add_ghana(totals)
    print("Adding arthitaya crops (NEW: melanonychia; also boosts leukonychia, "
          "beaus_lines, terrys_nails, onycholysis, healthy)...")
    add_arthitaya(totals)

    print("=" * 60)
    print(f"Done. Color-condition crops written to {OUT}")
    for split in SPLITS:
        split_dir = OUT / split
        if not split_dir.exists():
            continue
        per = {d.name: len(list(d.glob("*.jpg"))) for d in sorted(split_dir.iterdir()) if d.is_dir()}
        print(f"  {split}: {per}")
    print("\nNext: backend/venv/Scripts/python.exe ml/train/train_color_classifier.py "
          "--backbone mobilenet_v3_large")


if __name__ == "__main__":
    main()
