"""Honesty and data tool for the color/texture conditions.

These conditions use uncalibrated heuristic thresholds. Real-world accuracy is unknown
until calibrated against labeled photos.

This tool:
  PART A: Summarizes user feedback from the in-app "Does this match?" yes/no responses
          (from backend/nailiq.db, Feedback table). Flags conditions where >30% disagreed.
  PART B: Sweeps thresholds IF labeled photos are provided under
          data/color_eval/<condition>/{positive,negative}/ -- otherwise explains what's needed.
          Run scripts/build_color_eval_set.py first to populate these from the real,
          publicly licensed (CC BY 4.0) nail-disease datasets pulled by
          scripts/download_data.py -- it covers every condition below except
          melanonychia, which has no real labeled match in those sources.

Honest behavior: NEVER fabricates accuracy numbers. If data is missing, prints clear guidance.
Runs cleanly with no data present (no crashes, no empty confidence values printed).
"""

import sqlite3
import os
import sys
from pathlib import Path
import json

import cv2
import numpy as np


def get_repo_root():
    """Return the repo root (parent of backend/)."""
    # This script lives at ml/eval/calibrate_color.py
    script_dir = Path(__file__).resolve().parent.parent.parent
    return script_dir


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def part_a_feedback_summary():
    """Summarize user feedback from backend/nailiq.db."""
    print_section("PART A: Feedback Summary")

    repo_root = get_repo_root()
    db_path = repo_root / "backend" / "nailiq.db"

    if not db_path.exists():
        print(f"\nNo feedback database found at {db_path}")
        print("Feedback is collected from the in-app 'Does this match what you see?' "
              "yes/no on each result screen.")
        print("Re-run this script once users have submitted feedback.\n")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if feedback table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'"
        )
        if not cursor.fetchone():
            print(f"\nNo 'feedback' table in {db_path}")
            print("Feedback will be created once the app runs and users respond.\n")
            conn.close()
            return

        # Fetch all feedback
        cursor.execute(
            "SELECT label, shown_verdict, agreed FROM feedback ORDER BY label, shown_verdict"
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("\nNo feedback rows in the database yet.")
            print("Run the app, take scans, and respond to 'Does this match?' on the result.\n")
            return

        # Group by label and verdict
        feedback_by_label = {}
        for label, verdict, agreed in rows:
            if label not in feedback_by_label:
                feedback_by_label[label] = {}
            if verdict not in feedback_by_label[label]:
                feedback_by_label[label][verdict] = {"agreed": 0, "disagreed": 0}
            if agreed:
                feedback_by_label[label][verdict]["agreed"] += 1
            else:
                feedback_by_label[label][verdict]["disagreed"] += 1

        print("\nFeedback by condition and verdict:\n")
        for label in sorted(feedback_by_label.keys()):
            verdicts = feedback_by_label[label]
            total_agreed = sum(v["agreed"] for v in verdicts.values())
            total_disagreed = sum(v["disagreed"] for v in verdicts.values())
            total = total_agreed + total_disagreed

            disagree_pct = 100 * total_disagreed / total if total > 0 else 0
            review_flag = "  <-- REVIEW: > 30% disagreed" if disagree_pct > 30 else ""

            print(f"{label}:")
            for verdict in sorted(verdicts.keys()):
                v = verdicts[verdict]
                print(f"    {verdict}: {v['agreed']} agreed, {v['disagreed']} disagreed")
            print(f"  Total: {total_agreed}/{total} agreed ({100*total_agreed/total:.1f}%){review_flag}\n")

    except Exception as e:
        print(f"\nError reading feedback database: {e}\n")


EVAL_PAD_FRAC = 0.25


def load_image_padded(image_path, pad_frac=EVAL_PAD_FRAC):
    """Read an image and pad a margin around it for the eval pipeline.

    Public nail datasets are tight clinical close-ups where the finger fills the frame
    edge-to-edge, so preprocessing.extract_best_contour rejects ~100% of them as
    `contour_touches_border` (a gate that's correct for the app's own capture flow, where
    the finger is shot with background margin). Padding a constant border so the silhouette
    no longer touches the edge lets the same unmodified production pipeline localize the
    nail; verified to rescue ~100% of otherwise-rejected KNM images without distorting the
    per-pixel color/texture metrics (the pad is background, excluded from the silhouette).
    A photo that already has margin is unaffected by extra margin.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    h, w = img.shape[:2]
    m = int(pad_frac * max(h, w))
    return cv2.copyMakeBorder(img, m, m, m, m, cv2.BORDER_CONSTANT, value=(0, 0, 0))


def part_b_threshold_sweep():
    """Sweep thresholds on labeled photos if they exist."""
    print_section("PART B: Threshold Sweep")

    repo_root = get_repo_root()
    data_dir = repo_root / "data" / "color_eval"

    if not data_dir.exists():
        print(f"\nNo labeled data directory at {data_dir}")
        print("Run scripts/build_color_eval_set.py first -- it downloads/crops real,")
        print("publicly licensed (CC BY 4.0) nail-disease photos into")
        print(f"  {data_dir}/<condition>/positive/")
        print(f"  {data_dir}/<condition>/negative/")
        print("for every condition below except melanonychia (no real labeled match found).")
        print("You can also add your own .jpg/.jpeg/.png files to any condition's folders:")
        print("  - positive/ : photos with the condition present (outside typical range)")
        print("  - negative/ : control photos without the condition (within typical range)\n")
        print("Once photos are in place, re-run this script to sweep thresholds.\n")
        return

    # Lazy import: only load ml modules if we have data to process
    sys.path.insert(0, str(repo_root))
    try:
        from ml.infer import preprocessing, nail_region
        from ml.infer import (
            leukonychia, melanonychia, pallor, cyanosis, terrys_nails,
            lindsays_nails, onycholysis, beaus_lines, muehrckes_lines,
            splinter_hemorrhages, pitting,
        )
    except ImportError as e:
        print(f"\nFailed to import ml modules: {e}")
        print("Make sure the repo is on sys.path and ml/infer/*.py are accessible.\n")
        return

    # metric_func always takes `region` and returns a single float to compare
    # against threshold. Modules whose measure() returns a tuple are unwrapped here
    # to the one value that actually feeds that module's threshold comparison.
    conditions = {
        "leukonychia": {
            "metric_func": leukonychia.white_fraction,
            "threshold": leukonychia.LEUKONYCHIA_WHITE_FRAC_THRESHOLD,
        },
        "melanonychia": {
            "metric_func": melanonychia.band_contrast,
            "threshold": melanonychia.BAND_CONTRAST_THRESHOLD,
        },
        "pallor": {
            "metric_func": lambda r: pallor.measure(r)[1],  # redness_drop
            "threshold": pallor.PALLOR_REDNESS_DROP_THRESHOLD,
        },
        "cyanosis": {
            "metric_func": lambda r: cyanosis.measure(r)[1],  # bluer_than_skin
            "threshold": cyanosis.CYANOSIS_BLUER_THAN_SKIN,
        },
        "terrys_nails": {
            "metric_func": lambda r: terrys_nails.measure(r)[1],  # band_contrast
            "threshold": terrys_nails.TERRYS_CONTRAST_THRESHOLD,
        },
        "lindsays_nails": {
            "metric_func": lambda r: lindsays_nails.measure(r)[1],  # contrast
            "threshold": lindsays_nails.LINDSAY_CONTRAST_THRESHOLD,
        },
        "onycholysis": {
            "metric_func": lambda r: onycholysis.measure(r)[1],  # excess
            "threshold": onycholysis.ONYCHOLYSIS_EXCESS_THRESHOLD,
        },
        "beaus_lines": {
            "metric_func": beaus_lines.groove_depth,
            "threshold": beaus_lines.BEAUS_DEPTH_THRESHOLD,
        },
        "muehrckes_lines": {
            "metric_func": muehrckes_lines.count_bands,
            "threshold": muehrckes_lines.MUEHRCKE_BAND_COUNT_THRESHOLD,
        },
        "splinter_hemorrhages": {
            "metric_func": splinter_hemorrhages.count_streaks,
            "threshold": splinter_hemorrhages.SPLINTER_COUNT_THRESHOLD,
        },
        "pitting": {
            "metric_func": pitting.count_pits,
            "threshold": pitting.PITTING_COUNT_THRESHOLD,
        },
    }

    # Negatives are shared across every condition (same healthy-nail crops), and
    # region computation (contour + nail-plate localization) doesn't depend on which
    # condition's metric we're about to read off it -- only metric_func does. So the
    # expensive part (decode + contour + region) runs once per negative image total,
    # not once per condition, and the cheap per-condition metric_func is applied to
    # the cached region.
    neg_dir = data_dir / "_shared_negative"
    neg_images = (list(neg_dir.glob("*.jpg")) + list(neg_dir.glob("*.jpeg")) +
                  list(neg_dir.glob("*.png"))) if neg_dir.exists() else []

    neg_regions = []
    neg_skipped = 0
    if neg_images:
        print(f"\nComputing nail regions for {len(neg_images)} shared negative images "
              "(once, reused by every condition)...")
        for image_path in neg_images:
            try:
                img = load_image_padded(image_path)
                if img is None:
                    neg_skipped += 1
                    continue
                contour, val = preprocessing.extract_best_contour(img)
                if not val["is_valid"]:
                    neg_skipped += 1
                    continue
                region, reason = nail_region.compute_nail_region(img, contour)
                if region is None:
                    neg_skipped += 1
                    continue
                neg_regions.append(region)
            except Exception:
                neg_skipped += 1
        print(f"  {len(neg_regions)} usable, {neg_skipped} skipped")

    for cond_name, cond_info in conditions.items():
        cond_dir = data_dir / cond_name
        pos_dir = cond_dir / "positive"

        pos_images = list(pos_dir.glob("*.jpg")) + list(pos_dir.glob("*.jpeg")) + list(pos_dir.glob("*.png")) if pos_dir.exists() else []

        if not pos_images or not neg_regions:
            print(f"\n{cond_name.upper()}:")
            if not pos_dir.exists() or not pos_images:
                print(f"  No positive examples at {pos_dir}")
            if not neg_regions:
                print(f"  No usable negative examples at {neg_dir}")
            print(f"  Skipping threshold sweep (need both positive and negative photos).\n")
            continue

        print(f"\n{cond_name.upper()}:")
        print(f"  Loading {len(pos_images)} positive images...")

        metric_func = cond_info["metric_func"]
        current_threshold = cond_info["threshold"]

        metrics = {"positive": [], "negative": []}
        skipped = {"positive": 0, "negative": 0}

        for image_path in pos_images:
            try:
                img = load_image_padded(image_path)
                if img is None:
                    skipped["positive"] += 1
                    continue
                contour, val = preprocessing.extract_best_contour(img)
                if not val["is_valid"]:
                    skipped["positive"] += 1
                    continue
                region, reason = nail_region.compute_nail_region(img, contour)
                if region is None:
                    skipped["positive"] += 1
                    continue
                metric = metric_func(region)
                metrics["positive"].append(metric)
            except Exception:
                skipped["positive"] += 1

        for region in neg_regions:
            try:
                metrics["negative"].append(metric_func(region))
            except Exception:
                skipped["negative"] += 1

        if not metrics["positive"] or not metrics["negative"]:
            print(f"  Insufficient valid images (positive={len(metrics['positive'])}, "
                  f"negative={len(metrics['negative'])}, "
                  f"skipped pos={skipped['positive']}, neg={skipped['negative']})")
            print(f"  Check that images are valid photos with detectable nails.\n")
            continue

        print(f"  Processed: {len(metrics['positive'])} positive "
              f"({skipped['positive']} skipped), "
              f"{len(metrics['negative'])} negative "
              f"({skipped['negative']} skipped)")

        # Sweep thresholds
        all_metrics = np.array(metrics["positive"] + metrics["negative"])
        all_labels = np.array([1] * len(metrics["positive"]) + [0] * len(metrics["negative"]))

        # Candidate thresholds: quantiles from [0%, 10%, ..., 90%, 100%] of the positive set
        candidates = np.quantile(metrics["positive"], np.linspace(0, 1, 11))
        candidates = np.unique(np.concatenate([candidates, [current_threshold]]))

        best_threshold = None
        best_balanced_acc = -1

        for threshold in candidates:
            pred = (all_metrics > threshold).astype(int)
            tn = ((pred == 0) & (all_labels == 0)).sum()
            tp = ((pred == 1) & (all_labels == 1)).sum()
            fn = ((pred == 0) & (all_labels == 1)).sum()
            fp = ((pred == 1) & (all_labels == 0)).sum()

            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            balanced_acc = (sensitivity + specificity) / 2

            if balanced_acc > best_balanced_acc:
                best_balanced_acc = balanced_acc
                best_threshold = threshold

        # Report
        print(f"\n  Shipped threshold: {current_threshold:.4f}")
        print(f"  Recommended threshold: {best_threshold:.4f} "
              f"(balanced accuracy = {best_balanced_acc:.3f})")

        # Metrics at shipped vs recommended
        pred_shipped = (np.array(metrics["positive"] + metrics["negative"]) > current_threshold).astype(int)
        tp_shipped = ((pred_shipped == 1) & (all_labels == 1)).sum()
        tn_shipped = ((pred_shipped == 0) & (all_labels == 0)).sum()
        fn_shipped = ((pred_shipped == 0) & (all_labels == 1)).sum()
        fp_shipped = ((pred_shipped == 1) & (all_labels == 0)).sum()
        sens_shipped = tp_shipped / (tp_shipped + fn_shipped) if (tp_shipped + fn_shipped) > 0 else 0
        spec_shipped = tn_shipped / (tn_shipped + fp_shipped) if (tn_shipped + fp_shipped) > 0 else 0

        pred_rec = (np.array(metrics["positive"] + metrics["negative"]) > best_threshold).astype(int)
        tp_rec = ((pred_rec == 1) & (all_labels == 1)).sum()
        tn_rec = ((pred_rec == 0) & (all_labels == 0)).sum()
        fn_rec = ((pred_rec == 0) & (all_labels == 1)).sum()
        fp_rec = ((pred_rec == 1) & (all_labels == 0)).sum()
        sens_rec = tp_rec / (tp_rec + fn_rec) if (tp_rec + fn_rec) > 0 else 0
        spec_rec = tn_rec / (tn_rec + fp_rec) if (tn_rec + fp_rec) > 0 else 0

        print(f"\n  Shipped: {sens_shipped:.3f} sensitivity (miss {fn_shipped} positives), "
              f"{spec_shipped:.3f} specificity ({fp_shipped} false alarms on negatives)")
        print(f"  Recommended: {sens_rec:.3f} sensitivity (miss {fn_rec} positives), "
              f"{spec_rec:.3f} specificity ({fp_rec} false alarms on negatives)")
        print()


def main():
    """Run both parts."""
    repo_root = get_repo_root()
    print(f"\nCalibrate Color Conditions (NailIQ)")
    print(f"Repo: {repo_root}")

    part_a_feedback_summary()
    part_b_threshold_sweep()

    print_section("Summary")
    print("\nReminder: Current color thresholds are UNCALIBRATED rough estimates.")
    print("Real-world accuracy is unknown until labeled photo data is collected.\n")


if __name__ == "__main__":
    main()
