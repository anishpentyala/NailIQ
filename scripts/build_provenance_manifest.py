"""Per-image provenance manifest for data/raw/color_cls (the color-condition CNN's
training data). ATTRIBUTION.md and data/raw/LICENSES.md record provenance per
DATASET; this records it per IMAGE, which is what to check first if a specific
file's origin/license/label-confidence is ever in question -- e.g. exactly the
question that mattered when data/raw/nail-disease turned out to be contaminated
and every image sourced from it needed to be identified and removed.

Every crop written by scripts/build_color_classification_dataset.py already carries
a source prefix (`knm__`, `chaa__`, `ghana__`, `nihati__`, `anemia__`) before a `__`
separator -- this script reads that prefix back out per file and joins it against
the static per-source metadata below, rather than re-deriving provenance from
scratch. Run AFTER build_color_classification_dataset.py.

Usage (from repo root):
    backend/venv/Scripts/python.exe scripts/build_provenance_manifest.py
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COLOR_CLS = REPO / "data" / "raw" / "color_cls"
OUT = REPO / "data" / "raw" / "color_cls_provenance.csv"

# One entry per filename prefix used by build_color_classification_dataset.py.
# `diagnosis_confirmation` records what's actually known about how each source
# established its ground-truth label -- "community-labeled, method undocumented"
# is an honest answer, not a placeholder, for the three Roboflow Universe sets
# where no clinical methodology is published.
SOURCE_META = {
    "knm": {
        "dataset": "KNM Nail Disease Detection (nail-disease-detection-mxoqy)",
        "source_url": "https://universe.roboflow.com/knm/nail-disease-detection-mxoqy",
        "license": "CC BY 4.0",
        "diagnosis_confirmation": "community-labeled on Roboflow Universe; methodology undocumented",
    },
    "chaa": {
        "dataset": "chaa YOLOv8 Nails Segmentation (yolov8-nails-segmentation-ckvkd)",
        "source_url": "https://universe.roboflow.com/chaa/yolov8-nails-segmentation-ckvkd",
        "license": "CC BY 4.0",
        "diagnosis_confirmation": "community-labeled on Roboflow Universe; methodology undocumented; vetted 2026-09-15 for watermark/stock-photo contamination (0 confirmed)",
    },
    "ghana": {
        "dataset": "Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana (Asare, Appiahene & Donkoh, 2022, Mendeley Data)",
        "source_url": "https://data.mendeley.com/datasets/2xx4j3kjg2/1",
        "license": "CC BY 4.0",
        "diagnosis_confirmation": "clinician-labeled with paired hemoglobin (Hb) lab values per subject, per the dataset's published methodology",
    },
    "nihati": {
        "dataset": "Nail Disease Classification NIHATI (nail-disease-classification-nihati)",
        "source_url": "pulled via Roboflow SDK's public Project.search()/Project.image() API (no exportable version exists for this project)",
        "license": "CC BY 4.0",
        "diagnosis_confirmation": "community-labeled on Roboflow Universe; methodology undocumented; vetted 2026-09-16 for watermark/stock-photo contamination (0 confirmed)",
    },
    "anemia": {
        "dataset": "Anemia Nails Detection (nails-pceph, workspace anemia-hv9cy, v1)",
        "source_url": "https://universe.roboflow.com/anemia-hv9cy/nails-pceph",
        "license": "CC BY 4.0",
        "diagnosis_confirmation": "community-labeled on Roboflow Universe; methodology undocumented; only the anemic_nail class is used, vetted 2026-09-16",
    },
}

FIELDS = ["image_path", "split", "class_label", "source_prefix", "dataset",
          "source_url", "license", "diagnosis_confirmation"]


def main():
    if not COLOR_CLS.exists():
        raise SystemExit(f"{COLOR_CLS} not found -- run scripts/build_color_classification_dataset.py first.")

    rows, unknown_prefixes = [], set()
    for split_dir in sorted(COLOR_CLS.iterdir()):
        if not split_dir.is_dir():
            continue
        split = split_dir.name
        for slug_dir in sorted(split_dir.iterdir()):
            if not slug_dir.is_dir():
                continue
            for img_path in sorted(slug_dir.iterdir()):
                if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                    continue
                prefix = img_path.stem.split("__", 1)[0]
                meta = SOURCE_META.get(prefix)
                if meta is None:
                    unknown_prefixes.add(prefix)
                    meta = {"dataset": "UNKNOWN", "source_url": "UNKNOWN",
                             "license": "UNKNOWN", "diagnosis_confirmation": "UNKNOWN"}
                rows.append({
                    "image_path": str(img_path.relative_to(REPO)).replace("\\", "/"),
                    "split": split,
                    "class_label": slug_dir.name,
                    "source_prefix": prefix,
                    **meta,
                })

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT}")
    if unknown_prefixes:
        print(f"WARNING: unrecognized source prefixes (add to SOURCE_META): {sorted(unknown_prefixes)}")
    by_source = {}
    for r in rows:
        by_source[r["source_prefix"]] = by_source.get(r["source_prefix"], 0) + 1
    print("Per-source counts:", by_source)


if __name__ == "__main__":
    main()
