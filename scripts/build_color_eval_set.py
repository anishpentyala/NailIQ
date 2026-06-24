"""Build data/color_eval/<condition>/{positive,negative}/ from real labeled nail photos.

Source (downloaded by scripts/download_data.py, CC BY 4.0, YOLO detection format):
  - data/raw/nail-disease-detection-mxoqy  (KNM, 11 classes)

This gives ml/eval/calibrate_color.py real photos to sweep thresholds against, instead
of the uncalibrated constants the color/texture modules ship with.

A second dataset (tugas-akhir-kx2jl/nail-disease) was used in an earlier pass and then
DROPPED entirely -- see the note in scripts/download_data.py. It had Google-Image-scraped
images (thumbnail tokens in filenames) and a stock-photo watermark, so its CC BY 4.0
relicense claim isn't trustworthy. As a result, the conditions that ONLY it covered
(leukonychia, pallor, onycholysis, splinter_hemorrhages) have no vetted real-photo source
here and stay on their shipped heuristic thresholds, same as melanonychia (whose only
near-match, "Melanoma"/"Acral Lentiginous Melanoma", is a different condition -- a discrete
dark lesion, not a longitudinal pigmented band).

Two deliberate departures from the box-crop pattern in build_classification_dataset.py:

1. Uses the FULL source image, not the labeled box cropped+padded. The classical CV
   pipeline (ml/infer/nail_region.py) needs a whole finger silhouette to PCA-localize the
   nail plate -- fed a box tightly cropped to just the nail, the contour touches the image
   border on nearly every photo and gets rejected as "finger cropped out of frame." A first
   attempt that cropped to box+12% padding skipped 80-97% of images per condition for
   exactly this reason.

2. ONLY pulls from valid/test splits, never train -- the original unaugmented exports
   (Roboflow can bake mosaic augmentation + synthetic noise into train at export time).

PALLOR comes from a separate, properly-collected clinical source: the Ghana fingernail
anemia dataset (Mendeley Data, doi:10.17632/2xx4j3kjg2.1, CC BY 4.0) -- 710 photos taken
by lab personnel with blood-Hb ground truth, labeled anemic / non-anemic. We use anemic as
pallor-positive and non-anemic as its own (case-control) negatives. NOTE: it ships as ~4260
augmented PNGs (6-12 variants per patient); we keep one original per patient (no "(N)"
suffix) to avoid augmentation leakage. It is also nail-ONLY crops (no surrounding skin), so
it can't exercise the app's skin-relative pallor metric and is kept separate from the
KNM-derived sets. Download + extract manually first (it's a .rar, not Roboflow):
    curl -L -o data/raw/fingernails-ghana-anemia/Fingernails.rar \\
      https://data.mendeley.com/public-files/datasets/2xx4j3kjg2/files/e3d97e08-0c09-45bc-bde6-68c30e98319b/file_downloaded
    # sha256: 641ef99dd2b343eb00d0fc71b5062ba0a903046228440ab6b6311f81b0dc59ed
    bsdtar -xf Fingernails.rar -C data/raw/fingernails-ghana-anemia/

Usage (from repo root):
    backend/venv/Scripts/python.exe scripts/build_color_eval_set.py
"""

import re
import shutil
from pathlib import Path

import cv2
import yaml

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
OUT = REPO / "data" / "color_eval"

DATASETS = {
    "knm": RAW / "nail-disease-detection-mxoqy",
}

# Ghana anemia dataset (Mendeley, CC BY 4.0) -- pallor only; see module docstring.
GHANA_ROOT = RAW / "fingernails-ghana-anemia" / "Fingernails"

# condition -> [(dataset_key, class_name), ...]; multiple sources would be merged.
# Only KNM-backed conditions are listed -- the four that depended solely on the dropped
# nail-disease dataset (leukonychia, pallor, onycholysis, splinter_hemorrhages), plus
# melanonychia, have no vetted source and are intentionally absent (they keep their
# shipped heuristic thresholds).
CONDITION_SOURCES = {
    "cyanosis": [("knm", "Blue Finger")],
    "terrys_nails": [("knm", "Terry-s Nail")],
    "lindsays_nails": [("knm", "Lindsay-s Nail")],  # only ~2 imgs -- likely too few to trust
    "beaus_lines": [("knm", "Beaus Line")],
    "muehrckes_lines": [("knm", "Muehrckes Lines")],
    "pitting": [("knm", "Pitting")],
}

NEGATIVE_SOURCES = [("knm", "Healthy Nail")]

SPLITS = ["valid", "test"]  # train deliberately excluded -- see module docstring


def load_class_index(dataset_key):
    """Return {class_name: index} from a YOLO dataset's data.yaml."""
    data_yaml = DATASETS[dataset_key] / "data.yaml"
    names = yaml.safe_load(data_yaml.read_text())["names"]
    return {name: idx for idx, name in enumerate(names)}


def find_image_file(label_path):
    images_dir = label_path.parent.parent / "images"
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = images_dir / (label_path.stem + ext)
        if candidate.exists():
            return candidate
    return None


def collect_full_images(dataset_key, class_name, dest_dir, tag):
    """Copy each full (unaugmented) image that has >=1 box of class_name. Returns count."""
    class_idx = load_class_index(dataset_key).get(class_name)
    if class_idx is None:
        print(f"  !! class '{class_name}' not found in {dataset_key}, skipping")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    root = DATASETS[dataset_key]

    for split in SPLITS:
        labels_dir = root / split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in labels_dir.glob("*.txt"):
            has_class = any(
                line.strip().split() and int(line.strip().split()[0]) == class_idx
                for line in label_file.read_text().splitlines()
                if line.strip()
            )
            if not has_class:
                continue
            img_file = find_image_file(label_file)
            if img_file is None:
                continue
            dst = dest_dir / f"{tag}__{split}__{img_file.name}"
            shutil.copy(img_file, dst)
            written += 1

    return written


def _ghana_class(stem):
    """anemic / non / None from a Ghana filename (naming is inconsistent + has typos)."""
    s = stem.lower()
    if s.startswith("non"):
        return "non"
    if "anemic" in s or "anmeic" in s:  # 'Anmeic' typo appears in the dataset
        return "anemic"
    return None


def build_pallor_from_ghana():
    """Write pallor positive (anemic) + its own negatives (non-anemic) from the Ghana set.

    Keeps one ORIGINAL image per patient -- files without a '(N)' augmentation suffix or a
    trailing ' N' manual-duplicate suffix -- so the ~6-12 augmented variants per patient
    don't leak in and inflate n. Uses the dataset's own non-anemic photos as negatives
    (same camera/population = a proper case-control comparison), written to
    data/color_eval/pallor/negative so calibrate_color.py prefers them over the shared pool.
    """
    if not GHANA_ROOT.exists():
        print(f"  Ghana dataset not found at {GHANA_ROOT} -- skipping pallor "
              "(see module docstring for the manual download).")
        return

    def is_original(stem):
        return "(" not in stem and not re.search(r" \d+$", stem)

    pos_dir = OUT / "pallor" / "positive"
    neg_dir = OUT / "pallor" / "negative"
    pos_dir.mkdir(parents=True, exist_ok=True)
    neg_dir.mkdir(parents=True, exist_ok=True)

    n_pos = n_neg = 0
    for f in GHANA_ROOT.glob("*.png"):
        if not is_original(f.stem):
            continue
        cls = _ghana_class(f.stem)
        if cls == "anemic":
            shutil.copy(f, pos_dir / f"ghana__{f.name}")
            n_pos += 1
        elif cls == "non":
            shutil.copy(f, neg_dir / f"ghana__{f.name}")
            n_neg += 1
    print(f"  pallor <- Ghana anemia (CC BY 4.0): {n_pos} anemic positives, "
          f"{n_neg} non-anemic negatives (one original per patient)")


def main():
    if OUT.exists():
        print(f"Removing existing {OUT}")
        shutil.rmtree(OUT)

    # One shared negative pool, not copied per-condition: calibrate_color.py runs the
    # full nail-region CV pipeline once per file, so duplicating identical images into
    # every condition folder previously made it redo that work (and disk I/O) 10x over.
    print("\n=== Shared negative pool (healthy/normal nail, full images) ===")
    neg_dir = OUT / "_shared_negative"
    neg_total = 0
    for dataset_key, class_name in NEGATIVE_SOURCES:
        n = collect_full_images(dataset_key, class_name, neg_dir, tag=dataset_key)
        print(f"  {dataset_key}:{class_name} -> {n} images")
        neg_total += n
    print(f"  Total negative images: {neg_total}")

    print("\n=== Positive sets per condition (full images) ===")
    for condition, sources in CONDITION_SOURCES.items():
        pos_dir = OUT / condition / "positive"
        total = 0
        for dataset_key, class_name in sources:
            n = collect_full_images(dataset_key, class_name, pos_dir, tag=dataset_key)
            print(f"  {condition} <- {dataset_key}:{class_name} -> {n} images")
            total += n
        print(f"  {condition}: {total} positive\n")

    print("\n=== Pallor (separate clinical source, own negatives) ===")
    build_pallor_from_ghana()

    print("=" * 70)
    print(f"Done. Labeled eval sets written to {OUT}")
    print(f"Positives: {OUT}/<condition>/positive/")
    print(f"Negatives: {neg_dir} (shared), or <condition>/negative/ when present (pallor)")
    print("Spot-check a sample of images for watermarks/quality before trusting results.")
    print("Run: backend/venv/Scripts/python.exe ml/eval/calibrate_color.py")
    print("\nNOT covered (no vetted source): melanonychia, leukonychia, onycholysis, "
          "splinter_hemorrhages")


if __name__ == "__main__":
    main()
