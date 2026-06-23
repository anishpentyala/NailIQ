"""Evaluate the classifier on REAL phone photos -- the number that actually matters.

The training script's accuracy is on NailCheck's own held-out split: clean,
mostly top-down dataset images. That tells you little about how the model does on
a real phone photo. This runs the full inference path (ROI crop + TTA + calibrated
temperature, exactly what /analyze uses) over a folder of real photos you collect
and reports a confusion matrix + per-class recall.

Layout (folder name = true label; gitignored, these are personal photos):
    data/real_eval/healthy/*.jpg
    data/real_eval/clubbing/*.jpg
    data/real_eval/koilonychia/*.jpg

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/eval_real.py

Even 30-50 labeled phone shots make this meaningful. Recall on the condition
classes (did we catch the real signs?) is the screener metric to watch.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from ml.infer import classifier  # noqa: E402

REAL = REPO / "data" / "real_eval"
CLASSES = ["clubbing", "healthy", "koilonychia"]
IDX = {c: i for i, c in enumerate(CLASSES)}


def main():
    if not classifier.is_available():
        raise SystemExit("Model not available (train it first / install torch).")
    if not REAL.is_dir():
        raise SystemExit(
            f"No real-photo set at {REAL}.\n"
            "Create data/real_eval/<healthy|clubbing|koilonychia>/ and drop labeled "
            "phone photos in. See this file's docstring for the layout."
        )

    n = len(CLASSES)
    cm = np.zeros((n, n), dtype=int)
    low_conf = 0
    total = 0
    for label in CLASSES:
        d = REAL / label
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            total += 1
            pred, prob, _ = classifier.classify_bgr(bgr)
            if prob < classifier.CONFIDENCE_THRESHOLD:
                low_conf += 1  # would be reported "couldn't analyze", not a wrong guess
                continue
            cm[IDX[label]][IDX[pred]] += 1

    if total == 0:
        raise SystemExit(f"Found no images under {REAL}.")

    print(f"evaluated {total} real photos ({low_conf} below confidence floor -> inconclusive)\n")
    print("confusion matrix (rows = true, cols = predicted; excludes inconclusive):")
    print("            " + "  ".join(f"{c[:7]:>7s}" for c in CLASSES))
    for i, c in enumerate(CLASSES):
        print(f"  {c:10s} " + "  ".join(f"{cm[i][j]:7d}" for j in range(n)))

    print("\nper-class precision / recall (on confident predictions):")
    for i, c in enumerate(CLASSES):
        tp = cm[i][i]
        precision = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
        recall = tp / cm[i].sum() if cm[i].sum() else 0.0
        print(f"  {c:12s} P {precision:.3f}  R {recall:.3f}  (n={cm[i].sum()})")

    decided = cm.sum()
    if decided:
        print(f"\naccuracy on confident predictions {np.trace(cm) / decided:.3f}")


if __name__ == "__main__":
    main()
