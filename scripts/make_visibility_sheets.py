"""Contact sheets for a Haiku visibility audit of Han crops (same scheme as orient/visfilter/meta.json).

Usage: ml/venv/Scripts/python.exe scripts/make_visibility_sheets.py onychomycosis naildystrophy
Writes <class>_<k>.jpg (24 numbered crops each, 6x4) and meta_<class>.json under Han's orient/visfilter/.
Index of a crop = first_id + its tile number (0-23); judges write vis_<class>.json {"<index>": "Y"|"N"|"U"}.
"""
import json, random, sys
from pathlib import Path

import cv2, numpy as np

ROOT = Path("E:/NailIQ_data/raw/han-onychomycosis-figshare")
VF = ROOT / "orient" / "visfilter"
N_SHEETS, PER, COLS, SZ = 8, 24, 6, 160


def main():
    for cls in sys.argv[1:]:
        files = sorted((ROOT / "crops" / cls).glob("*.png"))
        random.Random(11).shuffle(files)
        files = files[:N_SHEETS * PER]
        meta = []
        for k in range(N_SHEETS):
            part = files[k * PER:(k + 1) * PER]
            tiles = []
            for t, f in enumerate(part):
                im = cv2.resize(cv2.imread(str(f)), (SZ, SZ))
                cv2.rectangle(im, (0, 0), (30, 18), (0, 0, 0), -1)
                cv2.putText(im, str(t), (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                tiles.append(im)
            rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]
            cv2.imwrite(str(VF / f"{cls}_{k}.jpg"), np.vstack(rows))
            meta.append({"sheet": f"{cls}_{k}.jpg", "cls": cls, "files": [str(p) for p in part], "first_id": k * PER})
        (VF / f"meta_{cls}.json").write_text(json.dumps(meta))
        print(cls, len(files), "crops,", N_SHEETS, "sheets")


if __name__ == "__main__":
    main()
