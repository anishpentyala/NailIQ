"""Write a tip-down copy of data/raw/color_cls to data/raw/color_cls_canon.

Every crop's fingertip direction is tagged by ml/infer/orientation.TipDirectionTagger and
the crop is rotated to tip-down. Crops the tagger is unsure about (confidence < MIN_CONF)
are left out rather than risk a wrongly rotated training image; counts are printed and the
per-crop tags go to orientation_manifest.csv. Splits and class folders are preserved.

Run from the repo root with ml/venv (needs torch):
    ml/venv/Scripts/python.exe scripts/canonicalize_color_dataset.py
"""
import csv, shutil, sys
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.infer import orientation

SRC = Path("data/raw/color_cls")
DST = Path("data/raw/color_cls_canon")
MIN_CONF = 0.6


def main():
    tagger = orientation.TipDirectionTagger()
    rows, kept, dropped = [], Counter(), Counter()
    for p in sorted(SRC.glob("*/*/*")):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        split, cls = p.parts[-3], p.parts[-2]
        out = DST / split / cls / p.name
        im = cv2.imread(str(p))
        if im is None:
            continue
        d, conf = tagger.tag(im)
        ok = conf >= MIN_CONF
        rows.append([str(p), split, cls, d, f"{conf:.3f}", int(ok)])
        if not ok:
            dropped[(split, cls)] += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), orientation.rotate_tip_down(im, d))
        kept[(split, cls)] += 1
    DST.mkdir(parents=True, exist_ok=True)
    with open(DST / "orientation_manifest.csv", "w", newline="") as f:
        csv.writer(f).writerows([["source", "split", "class", "tip_dir", "conf", "kept"], *rows])
    for split in ("train", "valid", "test"):
        k = sum(v for (s, _), v in kept.items() if s == split)
        d = sum(v for (s, _), v in dropped.items() if s == split)
        print(f"{split}: kept {k}, dropped {d}")
    print("tip direction before rotation:", Counter(r[3] for r in rows))


if __name__ == "__main__":
    main()
