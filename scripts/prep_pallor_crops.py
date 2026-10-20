"""Copy color_cls pallor crops (Ghana anemic patches + Roboflow anemia nail boxes) into the specialist crop cache
as data/raw/onych_app_crops/<split>/pallor/<src>__*.png so train_sign_specialist.py --target pallor can use them.
Healthy negatives already exist there (ghana__*, knm__*, chaa__*, ...). Splits are color_cls's own (Ghana patient-grouped)."""
import sys
from pathlib import Path
import cv2

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data/raw/color_cls"
OUT = REPO / "data/raw/onych_app_crops"
n = {}
for sp in ("train", "valid", "test"):
    for f in sorted((SRC / sp / "pallor").glob("*.jpg")):
        src = f.name.split("__")[0]
        dest = OUT / sp / "pallor" / (f"{src}__{f.stem}.png")
        if dest.exists():
            n[(sp, src)] = n.get((sp, src), 0) + 1
            continue
        im = cv2.imread(str(f))
        if im is None:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dest), im)
        n[(sp, src)] = n.get((sp, src), 0) + 1
print(n)
