"""Evaluate the live color-condition ensemble (ml/infer/color_classifier.py) on the
held-out color_cls/test split.

Sibling of eval_ensemble.py (geometry CNN). train_color_classifier.py prints each
backbone's solo accuracy, but production averages every registered member's
temperature-scaled, TTA'd softmax (color_classifier.classify_nail_bgr) -- this script
measures THAT number, the one that actually ships, and breaks out recall on the five
app conditions (the screener metric: don't miss a real sign).

The test crops are already nail plates, so they're classified directly (no bbox crop,
which is the inference step that turns a full photo into this same kind of crop).

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/eval_color_ensemble.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from ml.infer import color_classifier  # noqa: E402

TEST_DIR = REPO / "data" / "raw" / "color_cls" / "test"
EXTS = {".jpg", ".jpeg", ".png"}


def main():
    if not color_classifier.is_available():
        raise SystemExit("Color model not available (train it first / install torch).")
    s = color_classifier._load()
    classes = s["meta"]["classes"]
    app_conditions = set(s["meta"].get("app_conditions", []))
    backbones = [m["backbone"] for m in s["meta"]["ensemble"]]
    print(f"ensemble members: {backbones}\n")

    cm = np.zeros((len(classes), len(classes)), dtype=int)
    n_total = n_correct = 0

    for cls in classes:
        d = TEST_DIR / cls
        if not d.is_dir():
            continue
        true_idx = classes.index(cls)
        for p in sorted(d.iterdir()):
            if p.suffix.lower() not in EXTS:
                continue
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            label, _, _ = color_classifier.classify_nail_bgr(bgr)
            pred_idx = classes.index(label)
            cm[true_idx, pred_idx] += 1
            n_total += 1
            n_correct += int(pred_idx == true_idx)

    print("per-class precision / recall:")
    for i, c in enumerate(classes):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        flag = "  <- app condition recall" if c in app_conditions else ""
        print(f"  {c:16s} P {prec:.3f}  R {rec:.3f}  (n={cm[i, :].sum()}){flag}")

    app_idx = [i for i, c in enumerate(classes) if c in app_conditions or c == "healthy"]
    app_mask = np.zeros(len(classes), dtype=bool)
    app_mask[app_idx] = True
    app_total = cm[app_mask, :].sum()
    app_correct = sum(cm[i, i] for i in app_idx)
    print(f"\noverall ensemble test accuracy {n_correct / n_total:.3f}  (all {len(classes)} classes, n={n_total})")
    if app_total:
        print(f"accuracy on app conditions + healthy {app_correct / app_total:.3f}  (n={app_total})")


if __name__ == "__main__":
    main()
