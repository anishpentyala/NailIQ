"""Pull every nail-image dataset we can legally use into data/raw/.

All sources here are Roboflow Universe projects published under CC BY 4.0
(attribution required -- see data/raw/LICENSES.md, written by this script).

Usage:
    pip install -r scripts/requirements-data.txt
    set ROBOFLOW_API_KEY=xxxx            # Windows; export on macOS/Linux
    python scripts/download_data.py

Get a free key at https://app.roboflow.com/settings/api (any free account).
We can't ship a key -- Roboflow ties downloads to an account for attribution
and rate limiting. The key is the only manual step; everything else is automatic.

Detection datasets are pulled in YOLO format (images + boxes); classification
datasets in folder format (one subdir per class). Both land under data/raw/<name>/.
Cropping detection boxes into per-class images for the classifier is a later step
(scripts/build_classifier_set.py, not written yet).
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"

# workspace, project, version, export_format, task, attribution
DATASETS = [
    ("nails-btohy", "nailcheck-3xvkl", 1, "folder", "classification",
     "NailCheck (Clubbing, Healthy, Koilonychia, Pitting, Onychogryphosis, Terry's)"),
    ("knm", "nail-disease-detection-mxoqy", 4, "yolov8", "detection",
     "KNM Nail Disease Detection (~3022 images)"),
    ("livercheck-8v5ig", "nail-clubbing", 1, "yolov8", "detection",
     "LIVERCHECK+ Nail Clubbing"),
    ("allysoncarmelo07-gmail-com", "nail-disease-detection", 1, "yolov8", "detection",
     "Nail Disease Detection (Clubbing, Onychogryphosis)"),
    ("mist-r9pt1", "terry-s-nail-cbo00", 1, "yolov8", "detection",
     "MIST Terry's Nail"),
    ("chaa", "yolov8-nails-segmentation-ckvkd", 1, "yolov8", "segmentation",
     "chaa YOLOv8 Nails Segmentation (Healthy, Splinter Hemorrhage, Spoon Nail, Terry's "
     "Nail; ~1947 images) -- vetted 2026-09-15 (filename/EXIF/watermark screen, see "
     "data/raw/nail-disease's rejection note below for the contrast case)"),
    # NOTE: tugas-akhir-kx2jl/nail-disease was pulled here once and DELIBERATELY removed.
    # Despite its CC BY 4.0 tag, manual inspection found (a) its train split is Roboflow
    # mosaic-augmented (4 tiled images + synthetic noise, unusable as real photos) and
    # (b) several valid/test images are clearly scraped from Google Image Search
    # (filenames embed `images_q-tbn_ANd9GcS...` thumbnail tokens) and at least one
    # carries a third-party stock-photo watermark -- i.e. the uploader's relicense claim
    # is not trustworthy. Don't re-add it. KNM (above) is the vetted multi-condition source.
    #
    # data/raw/nail-disease (a DIFFERENT, un-prefixed "nail-disease" workspace project,
    # not tugas-akhir-kx2jl above) was pulled and used in training for ~3 months before
    # a 2026-09 audit found the same problem in it that the note above already flagged for
    # tugas-akhir-kx2jl: a corner-watermark heuristic scan (data/raw's own filename check
    # only caught 4 source photos/10 files) turned up real, visually-confirmed stock-photo
    # watermarks beyond that count. It has been dropped as a training source in
    # scripts/build_color_classification_dataset.py; the chaa dataset above exists to
    # backfill the splinter_hemorrhages coverage that removal costs. Don't re-add
    # nail-disease to that build script without re-running the same watermark screen.
]


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO / "backend" / ".env")
    except ImportError:
        pass

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        sys.exit(
            "ROBOFLOW_API_KEY not set.\n"
            "  1. Sign up free at https://app.roboflow.com\n"
            "  2. Copy your key from https://app.roboflow.com/settings/api\n"
            "  3. Add ROBOFLOW_API_KEY=<key> to backend/.env, then re-run."
        )

    try:
        from roboflow import Roboflow
    except ImportError:
        sys.exit("Run: pip install -r scripts/requirements-data.txt")

    RAW.mkdir(parents=True, exist_ok=True)
    rf = Roboflow(api_key=key)
    manifest = ["# Dataset sources & licenses\n",
                "All datasets below are CC BY 4.0 (attribution required).\n"]

    for ws, proj, ver, fmt, task, note in DATASETS:
        dest = RAW / proj
        print(f"\n=== {proj} v{ver} ({task}) -> {dest}")
        try:
            project = rf.workspace(ws).project(proj)
            project.version(ver).download(fmt, location=str(dest))
            manifest.append(
                f"- **{proj}** ({task}, format={fmt}) - {note}\n"
                f"  https://universe.roboflow.com/{ws}/{proj} - CC BY 4.0\n"
            )
        except Exception as e:  # noqa: BLE001 -- keep going on per-dataset failure
            print(f"  !! failed: {e}")
            manifest.append(f"- {proj}: DOWNLOAD FAILED ({e})\n")

    (RAW / "LICENSES.md").write_text("".join(manifest), encoding="utf-8")
    print(f"\nDone. Sources + licenses written to {RAW / 'LICENSES.md'}")
    print("NOTE: CC BY 4.0 requires you to credit each source in your "
          "submission/README.")


if __name__ == "__main__":
    main()
