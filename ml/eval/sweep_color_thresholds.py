"""Pick each CLASS_CONFIDENCE_THRESHOLD entry (ml/infer/color_classifier.py) on the
VALID split, then report its precision/recall on the TEST split at that fixed cutoff.

Every threshold previously in that file was swept AND reported on the same held-out
test split - classic cutoff-selection leakage, since the test set is supposed to be
touched exactly once, for a final unbiased number. This script separates the two: the
valid split picks the cutoff (the "highest cutoff that keeps recall >= 0.5" rule, the
same principle used when the floors were first set by hand), and only the test split's
number at that cutoff is ever printed as the reported precision/recall.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/sweep_color_thresholds.py

Expect the printed test-set precision to run a bit below the leaked numbers that used
to live in the code comments - that gap IS the leakage this script removes.
"""
import sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from ml.infer import color_classifier  # noqa: E402

DATA_ROOT = REPO / "data" / "raw" / "color_cls"
EXTS = {".jpg", ".jpeg", ".png"}

CANDIDATE_CUTOFFS = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95


def collect(split):
    """(true_label, pred_label, prob) for every image in a split."""
    records = []
    split_dir = DATA_ROOT / split
    if not split_dir.exists():
        return records
    for cls_dir in sorted(split_dir.iterdir()):
        if not cls_dir.is_dir():
            continue
        cls = cls_dir.name
        for p in sorted(cls_dir.iterdir()):
            if p.suffix.lower() not in EXTS:
                continue
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            label, prob, _ = color_classifier.classify_nail_bgr(bgr)
            records.append((cls, label, prob))
    return records


def precision_recall(records, target, cutoff):
    tp = fp = fn = 0
    for true_label, pred_label, prob in records:
        flagged = pred_label == target and prob >= cutoff
        if flagged and true_label == target:
            tp += 1
        elif flagged:
            fp += 1
        elif true_label == target:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    return prec, rec, tp, fp, fn


def pick_cutoff(valid_records, target):
    """Highest cutoff that still keeps recall >= 0.5 on VALID; falls back to the
    cutoff with the best precision if none clears that bar."""
    best_meeting_bar = None
    best_overall = None
    for cutoff in CANDIDATE_CUTOFFS:
        prec, rec, tp, fp, fn = precision_recall(valid_records, target, cutoff)
        if tp + fp == 0:
            continue
        if best_overall is None or prec > best_overall[1]:
            best_overall = (cutoff, prec, rec)
        if rec >= 0.5:
            best_meeting_bar = (cutoff, prec, rec)
    return best_meeting_bar or best_overall


def main():
    print("loading valid split predictions...")
    valid_records = collect("valid")
    print("loading test split predictions...")
    test_records = collect("test")
    print(f"valid n={len(valid_records)}  test n={len(test_records)}\n")

    targets = sorted(color_classifier.CLASS_CONFIDENCE_THRESHOLD.keys())
    print(f"{'class':22s} {'old(leaked)':>12s} {'new(valid-picked)':>18s} {'test P':>8s} {'test R':>8s}  n(test pos)")
    for target in targets:
        old = color_classifier.CLASS_CONFIDENCE_THRESHOLD.get(target)
        picked = pick_cutoff(valid_records, target)
        if picked is None:
            print(f"{target:22s} {old:>12.2f} {'no valid data':>18s}")
            continue
        cutoff, valid_prec, valid_rec = picked
        test_prec, test_rec, tp, fp, fn = precision_recall(test_records, target, cutoff)
        n_pos = sum(1 for t, _, _ in test_records if t == target)
        print(f"{target:22s} {old:>12.2f} {cutoff:>18.2f} {test_prec:>8.3f} {test_rec:>8.3f}  n={n_pos}")


if __name__ == "__main__":
    main()
