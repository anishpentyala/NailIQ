"""Build a tip-down (canonical orientation) Han dataset in data/raw/han_canon/.

Inputs: data/raw/han-onychomycosis-figshare/crops + orientation.csv (see
scripts/tag_nail_orientation.py). Keeps crops whose tip direction was tagged with
confidence >= MIN_CONF, rotates them tip-down, and splits BY SOURCE SHEET (a sheet is one
montage image, so one batch of photos; never by crop) with a stable hash. Sheets within a
class are split 70/15/15. Patient identity is not recorded in this dataset, so serial photos of
one patient can still sit in different sheets; treat eval numbers from it as optimistic.

NOT used for training until the Han watermark/duplicate audit has been run and the class
mapping below is approved (whitespot != leukonychia is an assumption, see MAP).
"""
import csv, hashlib, sys
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.infer import orientation

SRC = Path("data/raw/han-onychomycosis-figshare")
DST = Path("data/raw/han_canon")
MIN_CONF = 0.8
# 2026-10-16: Han's A1 labels are partly chart diagnoses, so a crop may show a normal nail. Each
# non-healthy class is therefore kept only where scripts/filter_han_visible_signs.py scores the sign
# as visible (p >= VIS_MIN; cross-val precision at 0.7: melanonychia ~0.80, onycholysis ~0.93,
# whitespot ~0.67). whitespot -> leukonychia mapping approved by the user 2026-10-16.
MAP = {"melanonychia": "melanonychia", "onycholysis": "onycholysis",
       "whitespot": "leukonychia", "normalnail": "healthy"}
VIS_MIN = 0.7
CAP = {"healthy": 3000}


def split_of(sheet):
    b = int(hashlib.md5(sheet.encode()).hexdigest(), 16) % 100
    return "train" if b < 70 else "valid" if b < 85 else "test"


def main():
    vis = {r[0]: float(r[2]) for r in list(csv.reader(open(SRC / "visible_signs.csv")))[1:]}
    n, rows = Counter(), []
    for crop, d, conf in list(csv.reader(open(SRC / "orientation.csv")))[1:]:
        cls_dir = Path(crop).parts[1]
        if cls_dir not in MAP or float(conf) < MIN_CONF:
            continue
        if cls_dir != "normalnail" and vis.get(crop.replace("\\", "/"), 0.0) < VIS_MIN:
            continue
        cls, sheet = MAP[cls_dir], Path(crop).name.rsplit("_", 1)[0]
        split = split_of(sheet + cls)
        if cls in CAP and n[(split, cls)] >= CAP[cls] * {"train": .7, "valid": .15, "test": .15}[split]:
            continue
        im = cv2.imread(str(SRC / crop))
        if im is None:
            continue
        out = DST / split / cls / Path(crop).name
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), orientation.rotate_tip_down(im, d))
        n[(split, cls)] += 1
        rows.append([str(out), split, cls, sheet, d, conf])
    with open(DST / "manifest.csv", "w", newline="") as f:
        csv.writer(f).writerows([["path", "split", "class", "sheet", "orig_tip_dir", "conf"], *rows])
    for k in sorted(n):
        print(k, n[k])


if __name__ == "__main__":
    main()
