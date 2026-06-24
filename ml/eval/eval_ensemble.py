"""Evaluate the live inference-time ensemble (ml/infer/classifier.py) on the
held-out merged/test split.

train_classifier.py reports each backbone's solo accuracy, but production
inference averages every registered member's temperature-scaled, TTA'd softmax
(classifier.classify_bgr) -- this script is the only place that measures THAT
number, which is what actually ships.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/eval_ensemble.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from ml.infer import classifier  # noqa: E402

TEST_DIR = REPO / "data" / "raw" / "merged" / "test"
EXTS = {".jpg", ".jpeg", ".png"}


def main():
    if not classifier.is_available():
        raise SystemExit("Model not available (train it first / install torch).")
    s = classifier._load()
    classes = s["meta"]["classes"]
    backbones = [m["backbone"] for m in s["meta"]["ensemble"]]
    print(f"ensemble members: {backbones}\n")

    cm = np.zeros((len(classes), len(classes)), dtype=int)
    n_total = n_correct = 0

    for cls in classes:
        d = TEST_DIR / cls
        if not d.is_dir():
            continue
        paths = [p for p in sorted(d.iterdir()) if p.suffix.lower() in EXTS]
        true_idx = classes.index(cls)
        for p in paths:
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            label, prob, _ = classifier.classify_bgr(bgr)
            pred_idx = classes.index(label)
            cm[true_idx, pred_idx] += 1
            n_total += 1
            n_correct += int(pred_idx == true_idx)

    print("confusion matrix (rows = true, cols = predicted):")
    header = "            " + "".join(f"{c[:8]:>9s}" for c in classes)
    print(header)
    for i, c in enumerate(classes):
        print(f"  {c:10s} " + "".join(f"{cm[i, j]:9d}" for j in range(len(classes))))

    print("\nper-class precision / recall:")
    for i, c in enumerate(classes):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        n = cm[i, :].sum()
        print(f"  {c:12s} P {prec:.3f}  R {rec:.3f}  (n={n})")

    print(f"\noverall ensemble test accuracy {n_correct / n_total:.3f}  (n={n_total})")


if __name__ == "__main__":
    main()
