"""App-style crops for the 2026-10-18 scope change (onychomycosis, psoriasis, nail dystrophy).

Every image goes through the production nail front end (ml.eval.eval_onycholysis_specialist_e2e.front_end:
framing sim -> quality gates -> nail_locator -> compute_nail_region -> padded bbox crop) and the crop is
written to data/raw/onych_app_crops/<split>/<class>/<src>__<stem>.png, the layout the specialist trainers use.
Splits: NIHATI-extra by md5(image id) 70/15/15; Han by source sheet (stem minus index) 70/15/15, like han_canon.
Han crops are kept only where the Haiku-trained visibility filter (scripts/filter_han_visible_signs.py, extended
to these classes) scores the sign as visible (p >= 0.7). Abstentions are listed in abstained_new.json.

Run from repo root: ml/venv/Scripts/python.exe scripts/build_new_sign_crops.py nihati han [--cap 1500]
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend"))
from ml.eval.eval_onycholysis_specialist_e2e import front_end  # noqa: E402

OUT = REPO / "data" / "raw" / "onych_app_crops"
NIH = Path("E:/NailIQ_data/raw/nihati_extra")
HAN = Path("E:/NailIQ_data/raw/han-onychomycosis-figshare")
VIS_MIN = 0.7


def bucket(key):
    b = int(hashlib.md5(key.encode()).hexdigest(), 16) % 100
    return "train" if b < 70 else "valid" if b < 85 else "test"


def run(items, abstained):
    n = 0
    for i, (src_path, split, cls, src) in enumerate(items):
        dest = OUT / split / cls / f"{src}__{src_path.stem}.png"
        if dest.exists():
            n += 1
            continue
        crop, reason = front_end(src_path)
        if crop is None:
            abstained.append({"path": str(src_path), "split": split, "cls": cls, "reason": reason})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dest), crop)
        n += 1
        if (i + 1) % 100 == 0:
            print(f"  {src} {i + 1}/{len(items)}", flush=True)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+", choices=["nihati", "han"])
    ap.add_argument("--cap", type=int, default=1500, help="max Han crops per class")
    ap.add_argument("--han-classes", default="onychomycosis,naildystrophy")
    ap.add_argument("--han-normal", type=int, default=0, help="also build this many Han normalnail crops as healthy negatives (src han)")
    a = ap.parse_args()
    abstained, items = [], []
    if "nihati" in a.sources:
        for cls in ("onychomycosis", "psoriasis"):
            for f in sorted((NIH / cls).glob("*")):
                if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    items.append((f, bucket(f.stem), cls, "nihati"))
    if "han" in a.sources:
        vis = {r[0]: float(r[2]) for r in list(csv.reader(open(HAN / "visible_signs.csv")))[1:]}
        for cls in a.han_classes.split(","):
            keep = sorted(c for c, p in vis.items() if c.startswith(f"crops/{cls}/") and p >= VIS_MIN)
            keep = [HAN / c for c in keep]
            sheets = {}
            for f in keep:
                sheets.setdefault(f.stem.rsplit("_", 1)[0], []).append(f)
            chosen, n = [], {"train": 0, "valid": 0, "test": 0}
            lim = {"train": a.cap * .7, "valid": a.cap * .15, "test": a.cap * .15}
            for sheet, fs in sorted(sheets.items()):
                sp = bucket(sheet + cls)
                for f in fs:
                    if n[sp] < lim[sp]:
                        chosen.append((f, sp, cls, "han")); n[sp] += 1
            print("han", cls, "visible", len(keep), "chosen", n, flush=True)
            items += chosen
    if a.han_normal and "han" in a.sources:
        import random
        sheets = {}
        for f in sorted((HAN / "crops" / "normalnail").glob("*.png")):
            sheets.setdefault(f.stem.rsplit("_", 1)[0], []).append(f)
        n = {"train": 0, "valid": 0, "test": 0}
        lim = {k: a.han_normal * v for k, v in (("train", .7), ("valid", .15), ("test", .15))}
        order = sorted(sheets); random.Random(5).shuffle(order)
        for sheet in order:
            sp = bucket(sheet + "healthy")
            for f in sheets[sheet]:
                if n[sp] < lim[sp]:
                    items.append((f, sp, "healthy", "han")); n[sp] += 1
        print("han normal chosen", n, flush=True)
    print(len(items), "images to process", flush=True)
    done = run(items, abstained)
    json.dump(abstained, open(OUT / "abstained_new.json", "w"), indent=1)
    print("written", done, "abstained", len(abstained))


if __name__ == "__main__":
    main()
