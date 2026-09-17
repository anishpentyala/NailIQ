"""Build data/raw/color_cls/{train,valid,test}/<slug>/ -- nail-plate crops for the
color-condition CNN (ml/train/train_color_classifier.py).

Sources (all Roboflow Universe, CC BY 4.0), merged by slug:
  1. data/raw/nail-disease-detection-mxoqy (KNM, 11 classes, YOLO detection) -- kept in
     its OWN clean image-level train/valid/test split (no reshuffle, no leakage).
  2. data/raw/fingernails-ghana-anemia -- pallor / darker-cohort healthy (see below).
  3. data/raw/yolov8-nails-segmentation-ckvkd (chaa, YOLO segmentation, 4 classes) --
     supplies splinter_hemorrhages (previously heuristic-only/false-positive-prone) and
     extra terrys_nails/koilonychia examples. RE-SPLIT by image stem, same reasoning as
     the removed nail-disease source below.
  4. data/raw/nail-disease-classification-nihati (NIHATI, folder classification,
     Roboflow has no generated export for this project -- see scripts/download_
     nihati notes in the Obsidian vault Change Log for how it was pulled via the
     public search/image API instead) -- RESTORES leukonychia/onycholysis/
     lindsays_nails coverage lost when data/raw/nail-disease was removed, using a
     DIFFERENT, independently-vetted source. RE-SPLIT by image id (its own split
     field wasn't leakage-audited the way KNM's was).
  5. data/raw/anemia-nails-detection (Roboflow, YOLO detection) -- adds 1,043+
     `anemic_nail` boxes to `pallor`. Only that one class is used: the dataset's
     other classes are tongue photos (irrelevant), and ~8.5% of its UNLABELED
     background images are traceable by filename to Pexels/Unsplash stock photos
     (a real, if minor, "CC BY 4.0 claim doesn't quite hold for the whole dataset"
     issue) -- but none of the labeled `anemic_nail` boxes come from those files
     (verified), so only the clinically-labeled crops are ingested here. RE-SPLIT
     by source-photo prefix (many images are Roboflow-augmented copies of the same
     underlying photo sharing a filename prefix before `_jpg.rf.<hash>`; splitting
     by raw filename would leak augmented copies of one photo across splits).

data/raw/nail-disease (25 classes) used to be a fourth source here, supplying
leukonychia, onycholysis, splinter_hemorrhages and lindsays_nails. It was REMOVED
2026-09 after a watermark audit: the June 2026 rejection of the similarly-named
tugas-akhir-kx2jl/nail-disease project (see scripts/download_data.py) never actually
covered this dataset, and a corner-watermark heuristic scan (ml/eval/ isn't where this
lives -- see the Obsidian vault Change Log) found visually-confirmed stock-photo
watermarks in it beyond the 4 photos its filenames alone flagged. Don't re-add it
without re-running that screen. chaa above backfills splinter_hemorrhages; onycholysis
and lindsays_nails currently have no CNN-covered source and fall back to the (already
near-chance) classical heuristic -- both are already in
ml/infer/validation_policy.UNVALIDATED_CONDITIONS, so this doesn't change what's shown
to users, only what trains the model.
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

# Third source: the chaa nails-segmentation set (data/raw/yolov8-nails-segmentation-ckvkd,
# Roboflow Universe, CC BY 4.0, YOLO segmentation, 4 classes: Healthy, Splinter
# Hemorrhage, Spoon Nail, Terry's Nail). Added 2026-09 to backfill splinter_hemorrhages
# CNN coverage after the nail-disease source (which used to supply it) was removed for
# watermark contamination -- see the module docstring. Its labels are polygon
# segmentation rows (class + variable-length x/y vertex list), not fixed-length YOLO
# detection boxes, so ingestion derives an axis-aligned bounding box from the polygon
# before reusing crop_box(). Its OWN split isn't reused -- same rationale as the old
# nail-disease source: re-split by image stem for a clean, leakage-safe train/valid/test
# (see resplit=True).
CHAA = REPO / "data" / "raw" / "yolov8-nails-segmentation-ckvkd"

# Fourth source: NIHATI's folder-classification set (data/raw/nail-disease-
# classification-nihati). Restores leukonychia/onycholysis/lindsays_nails coverage
# lost when nail-disease was removed, from a source independently vetted the same
# way (full EXIF/filename-regex/OCR/corner-watermark scan, 0 hits on all three;
# see Obsidian vault Change Log 2026-09-16). Images already sit in
# <split>/<slug>/ folders (reorganized from NIHATI's raw label tuples -- see the
# one-off reorganize script referenced in the vault), so ingestion is a straight
# copy, not a box crop.
NIHATI = REPO / "data" / "raw" / "nail-disease-classification-nihati"

# Fifth source: an anemia-detection YOLO set (data/raw/anemia-nails-detection).
# Only its `anemic_nail` class is used -- see the module docstring for why the
# other classes/images are excluded.
ANEMIA = REPO / "data" / "raw" / "anemia-nails-detection"

SPLITS = ["train", "valid", "test"]
BOX_PAD_FRAC = 0.15        # pad each side of the box; a little nail-fold context helps
MIN_CROP_PX = 24           # drop slivers that carry no usable colour/texture signal

# KNM class name -> internal slug. Lindsay-s Nail is intentionally absent (only 2 boxes
# in KNM; the nail-disease source that used to supply 176 more was removed for watermark
# contamination -- see the module docstring -- so lindsays_nails is now a near-empty
# class. It's already in ml/infer/validation_policy.UNVALIDATED_CONDITIONS, so this
# doesn't change what users see, but retrain output showing ~0 lindsays_nails examples
# is expected, not a bug.
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

# chaa class name -> internal slug. splinter_hemorrhages is the newly-covered app
# condition this ingestion exists for; the other three strengthen existing classes.
CHAA_SLUGS = {
    "Healthy": "healthy",
    "Splinter Hemorrhage": "splinter_hemorrhages",  # NEW app condition (was heuristic-only)
    "Spoon Nail": "koilonychia",                  # discrimination only (geometry owns it)
    "Terry-s nail": "terrys_nails",
}

# A fourth source, data/raw/nail-dataset-arthitaya (Kaggle, the only dataset found
# anywhere with melanonychia labels), was tried and DROPPED: its Kaggle license is
# "Unknown" (data/raw/LICENSES.md), an unresolved legal blocker for a model whose
# weights might ever be shared or shipped. Rather than train on unlicensed data and
# caveat it in a comment, melanonychia is CNN-uncovered -- it stays on the classical
# heuristic alone (ml/infer/melanonychia.py). Re-add only once a permissively-licensed
# melanonychia source turns up.


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


def _row_bbox(coords):
    """A label row's coordinate values (everything after the class index) -> a
    normalized (cx, cy, bw, bh) box. `coords` is either a 4-value YOLO detection box
    (cx, cy, bw, bh, used as-is) or a >=6-value, even-length YOLO segmentation polygon
    (x1, y1, x2, y2, ...), reduced to its axis-aligned bounding box -- chaa (the only
    polygon source so far) still crops the nail-plate box, not a pixel-accurate mask, so
    an AABB is all crop_box() needs."""
    if len(coords) == 4:
        return coords
    if len(coords) < 6 or len(coords) % 2:
        return None
    xs, ys = coords[0::2], coords[1::2]
    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
    return (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1


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
    """Crop every mapped box/polygon in a YOLO dataset into OUT/<split>/<slug>/. Handles
    both detection (fixed 5-field rows) and segmentation (variable-length polygon rows)
    label formats -- see _row_bbox().

    resplit=False: keep the dataset's own train/valid/test split (KNM ships a clean one).
    resplit=True:  ignore the source split and re-split by image stem via bucket_split
                   (for chaa, whose shipped split isn't leakage-checked against ours).
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
                if len(parts) < 5:
                    continue
                slug = idx_to_slug.get(int(parts[0]))
                if slug is None:
                    continue
                box = _row_bbox([float(v) for v in parts[1:]])
                if box is None:
                    continue
                if img is None:            # lazily load image only when a box is kept
                    img_file = find_image_file(label_file)
                    if img_file is None:
                        break
                    img = cv2.imread(str(img_file), cv2.IMREAD_COLOR)
                    if img is None:
                        break
                crop = crop_box(img, *box)
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


def add_nihati(totals):
    """Copy NIHATI's pre-sorted <split>/<slug>/*.png crops into OUT, re-splitting by
    image id (the id prefix already on each filename) via bucket_split -- each id is a
    distinct photo here, so no patient-grouping is needed, just a leakage-safe re-split
    independent of NIHATI's own (unaudited) split assignment."""
    if not NIHATI.exists():
        print(f"  nihati: dataset not found at {NIHATI} -- skipping")
        return
    added = {s: 0 for s in SPLITS}
    for src_split_dir in NIHATI.iterdir():
        if not src_split_dir.is_dir():
            continue
        for slug_dir in src_split_dir.iterdir():
            if not slug_dir.is_dir():
                continue
            for img_path in slug_dir.iterdir():
                if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                    continue
                image_id = img_path.stem.split("_", 1)[0]
                split = bucket_split(image_id)
                dst_dir = OUT / split / slug_dir.name
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img_path, dst_dir / f"nihati__{img_path.name}")
                added[split] += 1
                totals[split] = totals.get(split, 0) + 1
    print(f"  nihati: +{added}")


# anemia-nails-detection filenames are Roboflow-augmented copies of one source photo,
# e.g. "p102_jpg.rf.<hash>.jpg" -- strip the "_jpg.rf.<hash>" (or ".rf.<hash>") suffix
# to get the shared source-photo key so augmented copies never straddle a split.
_ANEMIA_SUFFIX_RE = re.compile(r"(_jpg)?\.rf\.[0-9a-f]+$", re.IGNORECASE)


def _anemia_source_key(stem):
    return _ANEMIA_SUFFIX_RE.sub("", stem)


def add_anemia(totals):
    """Crop only the `anemic_nail` boxes from the anemia YOLO set into OUT/<split>/pallor/.
    The dataset's other classes are tongue photos (not a nail condition) and its
    unlabeled background images include some Pexels/Unsplash stock photos -- neither is
    ingested here (see module docstring)."""
    if not ANEMIA.exists():
        print(f"  anemia: dataset not found at {ANEMIA} -- skipping")
        return
    added = {s: 0 for s in SPLITS}
    for src_split in SPLITS:
        labels_dir = ANEMIA / src_split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in labels_dir.glob("*.txt"):
            lines = [ln.split() for ln in label_file.read_text().splitlines()]
            boxes = [(float(p[1]), float(p[2]), float(p[3]), float(p[4]))
                     for p in lines if len(p) == 5 and p[0] == "0"]
            if not boxes:
                continue
            img_file = find_image_file(label_file)
            if img_file is None:
                continue
            img = cv2.imread(str(img_file), cv2.IMREAD_COLOR)
            if img is None:
                continue
            split = bucket_split(_anemia_source_key(label_file.stem))
            for bi, box in enumerate(boxes):
                crop = crop_box(img, *box)
                if crop is None:
                    continue
                dst_dir = OUT / split / "pallor"
                dst_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(dst_dir / f"anemia__{label_file.stem}__b{bi}.jpg"), crop)
                added[split] += 1
                totals[split] = totals.get(split, 0) + 1
    print(f"  anemia: +{added}")


def main():
    if not KNM.exists():
        raise SystemExit(f"KNM dataset not found at {KNM} -- run scripts/download_data.py first.")
    if OUT.exists():
        print(f"Removing existing {OUT}")
        shutil.rmtree(OUT)

    totals = {}
    print("Ingesting KNM box crops (keep source split)...")
    ingest_yolo(KNM, CLASS_SLUGS, "knm", totals, resplit=False)
    print("Ingesting chaa segmentation crops (re-split by image; adds splinter_hemorrhages)...")
    ingest_yolo(CHAA, CHAA_SLUGS, "chaa", totals, resplit=True)
    print("Adding Ghana fingernail-anemia crops (pallor / darker-cohort healthy)...")
    add_ghana(totals)
    print("Adding NIHATI crops (re-split by id; restores leukonychia/onycholysis/lindsays_nails)...")
    add_nihati(totals)
    print("Adding anemia anemic_nail crops (pallor)...")
    add_anemia(totals)
    # arthitaya (data/raw/nail-dataset-arthitaya) was DROPPED as a training source: its
    # Kaggle license is "Unknown" (see data/raw/LICENSES.md), an unresolved legal blocker
    # for any model whose weights might be shared or shipped. Rather than keep training on
    # unlicensed data while a caveat comment sits nearby, add_arthitaya() is no longer
    # called -- melanonychia drops back to CNN-uncovered / heuristic-only
    # (ml/infer/melanonychia.py), which is the same honest fallback this dataset's own
    # code comment described before it was ever integrated ("melanonychia stays
    # heuristic-only, no data anywhere else"). Re-enable only once the license is
    # confirmed permissive, or a differently-licensed melanonychia source is found.

    print("=" * 60)
    print(f"Done. Color-condition crops written to {OUT}")
    for split in SPLITS:
        split_dir = OUT / split
        if not split_dir.exists():
            continue
        per = {d.name: sum(1 for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
               for d in sorted(split_dir.iterdir()) if d.is_dir()}
        print(f"  {split}: {per}")
    print("\nNext: backend/venv/Scripts/python.exe ml/train/train_color_classifier.py "
          "--backbone mobilenet_v3_large")


if __name__ == "__main__":
    main()
