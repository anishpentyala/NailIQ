"""Build data/raw/color_cls/{train,valid,test}/<slug>/ -- nail-plate crops for the
color-condition CNN (ml/train/train_color_classifier.py).

Source: data/raw/nail-disease-detection-mxoqy (KNM, Roboflow Universe, CC BY 4.0,
YOLO detection format, 11 classes). Each labeled box is cropped (with a small pad)
to the nail plate and written as one classification sample, into the SAME split it
came from -- KNM already ships a clean image-level train/valid/test split, so we
don't reshuffle (no cross-split leakage), unlike the geometry merge which had to
rebuild its eval split.

Why box crops, not full images (the opposite of scripts/build_color_eval_set.py):
the color-eval set feeds the CLASSICAL pipeline (ml/infer/nail_region.py), which
needs a whole finger silhouette to PCA-localize the nail and rejects tight crops as
"finger cropped out of frame." A CNN has no such constraint -- it eats the raw
pixels -- so for it the tight nail-box crop is exactly right: it removes skin and
background so the model keys on the nail plate's colour/texture, which is the whole
signal for these conditions. At inference (ml/infer/color_classifier.py) the
counterpart crop is nail_region's detected nail bbox, so train/inference see
comparable nail-plate crops.

Class set: all KNM classes that have data EXCEPT "Lindsay-s Nail" (only 2 boxes in
the whole dataset -- too few to learn). That deliberately includes classes the app
does NOT individually report (Acral Lentiginous Melanoma, Onychogryphosis, Clubbing,
Koilonychia): keeping them as their own classes makes the classifier discriminate
rather than forcing, say, a melanoma nail into "pitting." The inference layer only
emits findings for the colour conditions the app screens (cyanosis, terrys_nails,
beaus_lines, muehrckes_lines, pitting); the extra classes exist purely to keep those
five honest.

Usage (from repo root):
    backend/venv/Scripts/python.exe scripts/build_color_classification_dataset.py
"""

import shutil
from pathlib import Path

import cv2
import yaml

REPO = Path(__file__).resolve().parent.parent
KNM = REPO / "data" / "raw" / "nail-disease-detection-mxoqy"
OUT = REPO / "data" / "raw" / "color_cls"

SPLITS = ["train", "valid", "test"]
BOX_PAD_FRAC = 0.15        # pad each side of the box; a little nail-fold context helps
MIN_CROP_PX = 24           # drop slivers that carry no usable colour/texture signal

# KNM class name -> internal slug. Lindsay-s Nail is intentionally absent (2 boxes).
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


def load_names():
    return yaml.safe_load((KNM / "data.yaml").read_text())["names"]


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


def main():
    if not KNM.exists():
        raise SystemExit(f"KNM dataset not found at {KNM} -- run scripts/download_data.py first.")
    if OUT.exists():
        print(f"Removing existing {OUT}")
        shutil.rmtree(OUT)

    names = load_names()
    idx_to_slug = {i: CLASS_SLUGS[n] for i, n in enumerate(names) if n in CLASS_SLUGS}

    totals = {}
    for split in SPLITS:
        labels_dir = KNM / split / "labels"
        if not labels_dir.exists():
            print(f"  {split}: (missing) -- skipping")
            continue
        n_written = 0
        for label_file in labels_dir.glob("*.txt"):
            img_file = None
            img = None
            for li, line in enumerate(label_file.read_text().splitlines()):
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                cls = int(parts[0])
                slug = idx_to_slug.get(cls)
                if slug is None:           # e.g. Lindsay-s Nail -> dropped
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
                cv2.imwrite(str(dst_dir / f"{label_file.stem}__b{li}.jpg"), crop)
                n_written += 1
        totals[split] = n_written
        print(f"  {split}: {n_written} crops")

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
