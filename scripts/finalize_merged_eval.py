"""Give the merged dataset a trustworthy eval split.

build_classification_dataset.py produced a strong, balanced *train* split, but its
perceptual-hash dedup was too aggressive on valid/test (a coarse 8x8 aHash treats
distinct nails as duplicates), collapsing them to a handful of images per class --
too small to evaluate or calibrate on.

This replaces merged/valid and merged/test with the ORIGINAL NailCheck valid/test
(clean, properly sized, and the consistent benchmark the project already reports
against), then removes any merged/train image that is a near-duplicate of an eval
image (leakage protection) using a finer difference-hash than the original build.

    backend/venv/Scripts/python.exe scripts/finalize_merged_eval.py

Idempotent-ish: rebuilds merged/valid and merged/test from NailCheck each run. Run
build_classification_dataset.py first.
"""

import shutil
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent
MERGED = REPO / "data" / "raw" / "merged"
NAILCHECK = REPO / "data" / "raw" / "nailcheck-3xvkl"

NAILCHECK_FOLDER = {"Clubbing": "clubbing", "Koilonychia": "koilonychia", "Healthy Nail": "healthy"}
CLASSES = ["clubbing", "koilonychia", "healthy"]
EXTS = {".jpg", ".jpeg", ".png"}
HAMMING_MAX = 5  # finer than the build's aHash; only drop genuine near-dup leakage


def dhash(path, size=8):
    """64-bit difference hash: compares adjacent columns of a (size+1 x size) gray image."""
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    img = cv2.resize(img, (size + 1, size))
    diff = img[:, 1:] > img[:, :-1]
    bits = 0
    for b in diff.flatten():
        bits = (bits << 1) | int(b)
    return bits


def rebuild_eval_from_nailcheck():
    for split in ("valid", "test"):
        dst_split = MERGED / split
        if dst_split.exists():
            shutil.rmtree(dst_split)
        counts = {}
        for folder, cls in NAILCHECK_FOLDER.items():
            src = NAILCHECK / split / folder
            dst = dst_split / cls
            dst.mkdir(parents=True, exist_ok=True)
            n = 0
            for p in src.iterdir() if src.is_dir() else []:
                if p.suffix.lower() in EXTS:
                    shutil.copy2(p, dst / f"nailcheck__{p.stem}.jpg")
                    n += 1
            counts[cls] = n
        print(f"{split} (from NailCheck): {counts}  total {sum(counts.values())}")


def dedup_train_against_eval():
    eval_hashes = []
    for split in ("valid", "test"):
        for cls in CLASSES:
            d = MERGED / split / cls
            for p in d.iterdir() if d.is_dir() else []:
                h = dhash(p)
                if h is not None:
                    eval_hashes.append(h)
    print(f"eval reference hashes: {len(eval_hashes)}")

    dropped = 0
    for cls in CLASSES:
        d = MERGED / "train" / cls
        for p in list(d.iterdir()) if d.is_dir() else []:
            if p.suffix.lower() not in EXTS:
                continue
            h = dhash(p)
            if h is None:
                continue
            if any(bin(h ^ eh).count("1") <= HAMMING_MAX for eh in eval_hashes):
                p.unlink()
                dropped += 1
    print(f"dropped {dropped} train images as near-duplicates of eval (leakage)")


def report():
    print("\nfinal merged dataset:")
    for split in ("train", "valid", "test"):
        row = {}
        for cls in CLASSES:
            d = MERGED / split / cls
            row[cls] = len(list(d.glob("*"))) if d.is_dir() else 0
        print(f"  {split:6s} {row}  total {sum(row.values())}")


if __name__ == "__main__":
    if not MERGED.is_dir():
        raise SystemExit("Run scripts/build_classification_dataset.py first.")
    rebuild_eval_from_nailcheck()
    dedup_train_against_eval()
    report()
