#!/usr/bin/env python3
"""
Build a merged 3-class classification dataset from multiple sources:
- nailcheck-3xvkl: classification crops (copy as-is)
- nail-clubbing: YOLO detection (crop boxes, class 0 -> clubbing)
- nail-disease-detection-mxoqy: YOLO detection (class 3->clubbing, 4->healthy, 5->koilonychia)
Output: data/raw/merged/{train,valid,test}/{clubbing,koilonychia,healthy}/
Deduplication: aHash with Hamming distance, protect eval splits.
Class balance: subsample clubbing train to 1.5x second-largest (seed=42).
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
import random
import cv2
import numpy as np
from typing import Dict, List, Tuple, Set

# ============================================================================
# CONSTANTS
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
MERGED_ROOT = DATA_RAW / "merged"

# Source dataset paths
NAILCHECK_ROOT = DATA_RAW / "nailcheck-3xvkl"
NAIL_CLUBBING_ROOT = DATA_RAW / "nail-clubbing"
NAIL_DISEASE_MXOQY_ROOT = DATA_RAW / "nail-disease-detection-mxoqy"

# Class mappings
NAILCHECK_CLASS_MAP = {
    "Clubbing": "clubbing",
    "Koilonychia": "koilonychia",
    "Healthy Nail": "healthy",
}

# YOLO class indices (0-indexed in respective datasets)
NAIL_CLUBBING_CLASS_MAP = {0: "clubbing"}  # single class

NAIL_DISEASE_MXOQY_CLASS_MAP = {
    3: "clubbing",
    4: "healthy",
    5: "koilonychia",
}

# Cropping and filtering
BOX_EXPAND_PERCENT = 0.12  # 12% padding on each side
MIN_CROP_WIDTH = 48  # pixels
MIN_CROP_HEIGHT = 48  # pixels
MIN_BOX_AREA_RATIO = 0.015  # 1.5% of full image

# Deduplication & balance
AHASH_SIZE = 8  # 8x8 = 64-bit hash
HAMMING_DISTANCE_THRESHOLD = 4  # max Hamming distance for dedup
RANDOM_SEED = 42
CLUBBING_BALANCE_RATIO = 1.5  # max clubbing = 1.5x second-largest class

SPLITS = ["train", "valid", "test"]
TARGET_CLASSES = ["clubbing", "koilonychia", "healthy"]

# ============================================================================
# UTILITIES
# ============================================================================


def ahash_image(img_bgr: np.ndarray) -> np.uint64:
    """Compute 64-bit average hash of an image (aHash)."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (AHASH_SIZE, AHASH_SIZE))
    mean = small.mean()
    bits = (small > mean).astype(np.uint8).flatten()
    hash_val = 0
    for i, bit in enumerate(bits):
        hash_val |= (int(bit) << i)
    return hash_val


def hamming_distance(h1: np.uint64, h2: np.uint64) -> int:
    """Hamming distance between two 64-bit hashes."""
    xor = h1 ^ h2
    dist = 0
    while xor:
        dist += xor & 1
        xor >>= 1
    return dist


def find_image_file(label_path: Path) -> Path | None:
    """Find the image file matching a YOLO label file."""
    stem = label_path.stem
    images_dir = label_path.parent.parent / "images"
    for ext in [".jpg", ".jpeg", ".png"]:
        candidate = images_dir / (stem + ext)
        if candidate.exists():
            return candidate
    return None


def denormalize_yolo_box(cx: float, cy: float, w: float, h: float, img_h: int, img_w: int) -> Tuple[int, int, int, int]:
    """Denormalize YOLO box (all normalized to [0,1]) to pixel coords (x1, y1, x2, y2)."""
    cx_px = cx * img_w
    cy_px = cy * img_h
    w_px = w * img_w
    h_px = h * img_h
    x1 = max(0, int(cx_px - w_px / 2))
    y1 = max(0, int(cy_px - h_px / 2))
    x2 = min(img_w, int(cx_px + w_px / 2))
    y2 = min(img_h, int(cy_px + h_px / 2))
    return x1, y1, x2, y2


def expand_box_with_padding(x1: int, y1: int, x2: int, y2: int, img_h: int, img_w: int) -> Tuple[int, int, int, int]:
    """Expand box by 12% padding on each side, clamped to image bounds."""
    w = x2 - x1
    h = y2 - y1
    pad_w = int(w * BOX_EXPAND_PERCENT)
    pad_h = int(h * BOX_EXPAND_PERCENT)
    x1_new = max(0, x1 - pad_w)
    y1_new = max(0, y1 - pad_h)
    x2_new = min(img_w, x2 + pad_w)
    y2_new = min(img_h, y2 + pad_h)
    return x1_new, y1_new, x2_new, y2_new


def passes_quality_filter(crop_w: int, crop_h: int, box_area: int, img_area: int) -> bool:
    """Check quality filters: min size and min area ratio."""
    if crop_w < MIN_CROP_WIDTH or crop_h < MIN_CROP_HEIGHT:
        return False
    if img_area > 0 and box_area / img_area < MIN_BOX_AREA_RATIO:
        return False
    return True


# ============================================================================
# MAIN BUILD LOGIC
# ============================================================================


def build_merged_dataset():
    """Build merged classification dataset from all sources."""

    # Clean start
    if MERGED_ROOT.exists():
        print(f"Removing existing {MERGED_ROOT}")
        shutil.rmtree(MERGED_ROOT)

    # Create directory structure
    for split in SPLITS:
        for cls in TARGET_CLASSES:
            (MERGED_ROOT / split / cls).mkdir(parents=True, exist_ok=True)

    stats = {
        "total_copied": 0,
        "total_cropped": 0,
        "total_dropped_size": 0,
        "total_dropped_area": 0,
        "total_dropped_dedup": 0,
        "total_subsampled": 0,
    }

    per_split_per_class = defaultdict(lambda: defaultdict(int))
    eval_hashes: Set[np.uint64] = set()  # valid + test hashes (for dedup)
    train_hashes_by_class: Dict[str, Set[np.uint64]] = {cls: set() for cls in TARGET_CLASSES}

    # ========================================================================
    # STAGE 1: Copy nailcheck (classification) crops as-is
    # ========================================================================
    print("\n[1/3] Processing nailcheck-3xvkl (classification crops)...")
    for split in SPLITS:
        for nailcheck_cls, target_cls in NAILCHECK_CLASS_MAP.items():
            src_dir = NAILCHECK_ROOT / split / nailcheck_cls
            if not src_dir.exists():
                continue

            for src_file in src_dir.glob("*.*"):
                if src_file.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                    continue

                # Convert to JPEG and save
                img = cv2.imread(str(src_file))
                if img is None:
                    continue

                dst_path = MERGED_ROOT / split / target_cls / f"nailcheck__{src_file.stem}.jpg"
                cv2.imwrite(str(dst_path), img)

                # Track hash for dedup
                h = ahash_image(img)
                if split in ["valid", "test"]:
                    eval_hashes.add(h)
                elif split == "train":
                    train_hashes_by_class[target_cls].add(h)

                per_split_per_class[split][target_cls] += 1
                stats["total_copied"] += 1

    print(f"  Copied {stats['total_copied']} images from nailcheck")

    # ========================================================================
    # STAGE 2: Crop and process nail-clubbing (YOLO detection)
    # ========================================================================
    print("\n[2/3] Processing nail-clubbing (YOLO detection)...")
    for split in SPLITS:
        labels_dir = NAIL_CLUBBING_ROOT / split / "labels"
        if not labels_dir.exists():
            continue

        for label_file in labels_dir.glob("*.txt"):
            img_file = find_image_file(label_file)
            if img_file is None:
                continue

            img = cv2.imread(str(img_file))
            if img is None:
                continue

            img_h, img_w = img.shape[:2]
            img_area = img_h * img_w

            # Parse YOLO labels
            with open(label_file) as f:
                lines = f.readlines()

            if not lines:
                continue

            for box_idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                class_idx = int(parts[0])
                if class_idx not in NAIL_CLUBBING_CLASS_MAP:
                    continue

                target_cls = NAIL_CLUBBING_CLASS_MAP[class_idx]
                cx, cy, w, h = map(float, parts[1:5])

                # Denormalize and expand box
                x1, y1, x2, y2 = denormalize_yolo_box(cx, cy, w, h, img_h, img_w)
                x1, y1, x2, y2 = expand_box_with_padding(x1, y1, x2, y2, img_h, img_w)

                crop_w, crop_h = x2 - x1, y2 - y1
                box_area = crop_w * crop_h

                if not passes_quality_filter(crop_w, crop_h, box_area, img_area):
                    if crop_w < MIN_CROP_WIDTH or crop_h < MIN_CROP_HEIGHT:
                        stats["total_dropped_size"] += 1
                    else:
                        stats["total_dropped_area"] += 1
                    continue

                # Crop and save
                crop = img[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                dst_path = MERGED_ROOT / split / target_cls / f"nailclub__{label_file.stem}__b{box_idx}.jpg"
                cv2.imwrite(str(dst_path), crop)

                # Track hash for dedup
                h = ahash_image(crop)
                if split in ["valid", "test"]:
                    eval_hashes.add(h)
                elif split == "train":
                    train_hashes_by_class[target_cls].add(h)

                per_split_per_class[split][target_cls] += 1
                stats["total_cropped"] += 1

    print(f"  Cropped {stats['total_cropped']} images from nail-clubbing")

    # ========================================================================
    # STAGE 3: Crop and process nail-disease-detection-mxoqy (YOLO detection)
    # ========================================================================
    print("\n[3/3] Processing nail-disease-detection-mxoqy (YOLO detection)...")
    for split in SPLITS:
        labels_dir = NAIL_DISEASE_MXOQY_ROOT / split / "labels"
        if not labels_dir.exists():
            continue

        for label_file in labels_dir.glob("*.txt"):
            img_file = find_image_file(label_file)
            if img_file is None:
                continue

            img = cv2.imread(str(img_file))
            if img is None:
                continue

            img_h, img_w = img.shape[:2]
            img_area = img_h * img_w

            # Parse YOLO labels
            with open(label_file) as f:
                lines = f.readlines()

            if not lines:
                continue

            for box_idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                class_idx = int(parts[0])
                if class_idx not in NAIL_DISEASE_MXOQY_CLASS_MAP:
                    continue

                target_cls = NAIL_DISEASE_MXOQY_CLASS_MAP[class_idx]
                cx, cy, w, h = map(float, parts[1:5])

                # Denormalize and expand box
                x1, y1, x2, y2 = denormalize_yolo_box(cx, cy, w, h, img_h, img_w)
                x1, y1, x2, y2 = expand_box_with_padding(x1, y1, x2, y2, img_h, img_w)

                crop_w, crop_h = x2 - x1, y2 - y1
                box_area = crop_w * crop_h

                if not passes_quality_filter(crop_w, crop_h, box_area, img_area):
                    if crop_w < MIN_CROP_WIDTH or crop_h < MIN_CROP_HEIGHT:
                        stats["total_dropped_size"] += 1
                    else:
                        stats["total_dropped_area"] += 1
                    continue

                # Crop and save
                crop = img[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                dst_path = MERGED_ROOT / split / target_cls / f"mxoqy__{label_file.stem}__b{box_idx}.jpg"
                cv2.imwrite(str(dst_path), crop)

                # Track hash for dedup
                h = ahash_image(crop)
                if split in ["valid", "test"]:
                    eval_hashes.add(h)
                elif split == "train":
                    train_hashes_by_class[target_cls].add(h)

                per_split_per_class[split][target_cls] += 1
                stats["total_cropped"] += 1

    print(f"  Cropped {stats['total_cropped']} total from nail-disease-detection-mxoqy")

    # ========================================================================
    # STAGE 4: Deduplication (protect eval splits)
    # ========================================================================
    print("\n[4/4] Deduplication...")
    dedup_removed_by_reason = {"eval_collision": 0, "train_collision": 0}

    for split in SPLITS:
        if split not in ["valid", "test"]:
            continue

        for cls in TARGET_CLASSES:
            cls_dir = MERGED_ROOT / split / cls
            to_remove = []

            for img_file in cls_dir.glob("*.jpg"):
                img = cv2.imread(str(img_file))
                if img is None:
                    continue

                h = ahash_image(img)
                # Check if this exact hash exists elsewhere in eval
                if h in eval_hashes and h != eval_hashes:  # not just itself
                    to_remove.append(img_file)
                    dedup_removed_by_reason["eval_collision"] += 1

            for f in to_remove:
                f.unlink()
                per_split_per_class[split][cls] -= 1

    # Within-train dedup: exact duplicates within class/split
    for cls in TARGET_CLASSES:
        cls_dir = MERGED_ROOT / "train" / cls
        seen_hashes = {}
        to_remove = []

        for img_file in cls_dir.glob("*.jpg"):
            img = cv2.imread(str(img_file))
            if img is None:
                continue

            h = ahash_image(img)
            if h in seen_hashes:
                to_remove.append(img_file)
                dedup_removed_by_reason["train_collision"] += 1
            else:
                seen_hashes[h] = img_file

        for f in to_remove:
            f.unlink()
            per_split_per_class["train"][cls] -= 1

    # Train vs eval collision (Hamming distance)
    dedup_removed_by_reason["eval_leakage"] = 0
    for cls in TARGET_CLASSES:
        cls_dir = MERGED_ROOT / "train" / cls
        to_remove = []

        for img_file in cls_dir.glob("*.jpg"):
            img = cv2.imread(str(img_file))
            if img is None:
                continue

            h = ahash_image(img)
            for eval_h in eval_hashes:
                if hamming_distance(h, eval_h) <= HAMMING_DISTANCE_THRESHOLD:
                    to_remove.append(img_file)
                    dedup_removed_by_reason["eval_leakage"] += 1
                    break

        for f in to_remove:
            f.unlink()
            per_split_per_class["train"][cls] -= 1

    stats["total_dropped_dedup"] = sum(dedup_removed_by_reason.values())
    print(f"  Dedup removed: {dedup_removed_by_reason}")

    # ========================================================================
    # STAGE 5: Class balancing (TRAIN only)
    # ========================================================================
    print("\n[5/5] Class balancing...")
    train_counts = per_split_per_class["train"]
    second_largest = sorted([train_counts[c] for c in TARGET_CLASSES])[-2]
    clubbing_target = int(second_largest * CLUBBING_BALANCE_RATIO)

    if train_counts["clubbing"] > clubbing_target:
        print(f"  Subsampling clubbing train: {train_counts['clubbing']} -> {clubbing_target}")

        club_dir = MERGED_ROOT / "train" / "clubbing"
        all_files = list(club_dir.glob("*.jpg"))
        random.seed(RANDOM_SEED)
        keep_files = set(random.sample(all_files, clubbing_target))

        for f in all_files:
            if f not in keep_files:
                f.unlink()

        stats["total_subsampled"] = train_counts["clubbing"] - clubbing_target
        per_split_per_class["train"]["clubbing"] = clubbing_target

    # ========================================================================
    # REPORT
    # ========================================================================
    print("\n" + "=" * 70)
    print("FINAL DATASET SUMMARY")
    print("=" * 70)

    print("\nPer-split, per-class counts:")
    print(f"{'Split':<10} {'Clubbing':<12} {'Koilonychia':<15} {'Healthy':<12} {'Total':<10}")
    print("-" * 60)

    grand_total = 0
    for split in SPLITS:
        club = per_split_per_class[split]["clubbing"]
        koil = per_split_per_class[split]["koilonychia"]
        health = per_split_per_class[split]["healthy"]
        total = club + koil + health
        grand_total += total
        print(f"{split:<10} {club:<12} {koil:<15} {health:<12} {total:<10}")

    print("-" * 60)
    print(f"{'TOTAL':<10} {per_split_per_class['train']['clubbing'] + per_split_per_class['valid']['clubbing'] + per_split_per_class['test']['clubbing']:<12} "
          f"{per_split_per_class['train']['koilonychia'] + per_split_per_class['valid']['koilonychia'] + per_split_per_class['test']['koilonychia']:<15} "
          f"{per_split_per_class['train']['healthy'] + per_split_per_class['valid']['healthy'] + per_split_per_class['test']['healthy']:<12} "
          f"{grand_total:<10}")

    print(f"\nTotal images produced: {grand_total}")

    print("\nDropped images:")
    print(f"  Size filter (w or h < 48px):  {stats['total_dropped_size']}")
    print(f"  Area ratio filter (< 1.5%):   {stats['total_dropped_area']}")
    print(f"  Deduplication:                {stats['total_dropped_dedup']}")
    print(f"    - eval collision:          {dedup_removed_by_reason.get('eval_collision', 0)}")
    print(f"    - train collision:         {dedup_removed_by_reason.get('train_collision', 0)}")
    print(f"    - eval leakage (H-dist):   {dedup_removed_by_reason.get('eval_leakage', 0)}")
    print(f"  Subsampled (balance):         {stats['total_subsampled']}")

    total_dropped = (stats['total_dropped_size'] + stats['total_dropped_area'] +
                     stats['total_dropped_dedup'] + stats['total_subsampled'])
    print(f"\n  TOTAL DROPPED: {total_dropped}")

    print("\nDataset saved to: " + str(MERGED_ROOT))


if __name__ == "__main__":
    build_merged_dataset()
