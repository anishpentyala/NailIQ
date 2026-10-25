"""Does the on-device (ONNX) pipeline give the same answers as the server (PyTorch) pipeline?

Runs held-out dataset photos through ml.infer.pipeline.analyze twice in one process - once normally, once with
NAILIQ_BACKEND=onnx - and compares every finding (verdict, and the model probabilities where present).
    ml/venv/Scripts/python.exe ml/eval/parity_onnx.py --n 150
"""
import argparse
import base64
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ml.eval.eval_end_to_end import b64, gather  # noqa: E402
from ml.infer import pipeline  # noqa: E402


def run(side, top, backend):
    if backend == "onnx":
        os.environ["NAILIQ_BACKEND"] = "onnx"
    else:
        os.environ.pop("NAILIQ_BACKEND", None)
    return pipeline.analyze(side, top)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--split", default="test")
    args = ap.parse_args()

    _, buf = cv2.imencode(".jpg", np.full((64, 64, 3), 128, dtype=np.uint8))
    side = base64.b64encode(buf).decode()
    items = sorted(gather(args.split).items(), key=lambda kv: str(kv[0]))
    step = max(1, len(items) // args.n)
    items = items[::step][: args.n]

    same_verdict = total = 0
    max_prob_diff = 0.0
    flips = []
    for i, (path, labels) in enumerate(items):
        top = b64(path)
        a = run(side, top, "torch")
        b = run(side, top, "onnx")
        fa = {f["label"]: f for f in a["findings"]}
        fb = {f["label"]: f for f in b["findings"]}
        assert fa.keys() == fb.keys(), (path, set(fa) ^ set(fb))
        for label in fa:
            total += 1
            if fa[label]["verdict"] == fb[label]["verdict"]:
                same_verdict += 1
            else:
                flips.append((path.name, label, fa[label]["verdict"], fb[label]["verdict"]))
            pa = (fa[label].get("ml") or {}).get("probs") or {}
            pb = (fb[label].get("ml") or {}).get("probs") or {}
            for k in pa.keys() & pb.keys():
                max_prob_diff = max(max_prob_diff, abs(pa[k] - pb[k]))
        if i % 20 == 0:
            print(f"  {i + 1}/{len(items)}  verdict agreement so far {same_verdict}/{total}", flush=True)
    print(f"\nimages {len(items)}  findings {total}  identical verdicts {same_verdict} ({100 * same_verdict / total:.2f}%)")
    print(f"max class-probability difference {max_prob_diff:.3f}")
    for f in flips[:30]:
        print("  FLIP", f)


if __name__ == "__main__":
    main()
