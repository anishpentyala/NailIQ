"""False-positive scan on the Hb skin+fingernail photo set (Yakimov et al. 2024, Figshare, CC0 record).

EVALUATION ONLY - never trained on. One photo per patient with 3 labelled nail boxes. Each nail is cut out as a
single-finger window (nail box padded, extended toward the finger body), sent through /analyze with a blank side
photo, and the verdict the user would see is counted. No disease labels exist, so every flag is an UPPER BOUND
on false alarms for a normal nail (pallor is skipped: some patients are anaemic). Hb < 120 g/L (women) /
< 130 (men) patients are reported separately for context.

Run from repo root: ml/venv/Scripts/python.exe ml/eval/scan_hb_nails.py [--root E:/NailIQ_data/raw/hb_skin_nails_figshare]
"""
import argparse, ast, base64, csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2, numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend"))
from ml.eval.eval_color_sensitivity import create_eval_client  # noqa: E402

SCALE = 1.0
PADV, PADL, PADR = 1.0, 1.0, 3.0
enc = lambda im: base64.b64encode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tobytes()).decode()  # noqa: E731


def window(img, box):
    y0, x0, y1, x1 = box; w, h = x1 - x0, y1 - y0     # metadata boxes are [y0, x0, y1, x1]
    H, W = img.shape[:2]
    # fingers in this set point left; keep the whole fingertip and extend to the right (finger body)
    cy0, cy1 = max(0, int(y0 - PADV * h)), min(H, int(y1 + PADV * h))
    cx0, cx1 = max(0, int(x0 - PADL * w)), min(W, int(x1 + PADR * w))
    crop = img[cy0:cy1, cx0:cx1]
    ch, cw = crop.shape[:2]
    nb = [float(np.clip(v, 0.0, 1.0)) for v in ((x0 - cx0) / cw, (y0 - cy0) / ch, (x1 - cx0) / cw, (y1 - cy0) / ch)]
    # the source photos are 800x600 with ~50px nails; a phone close-up has a nail 3x+ larger, so upscale to match
    return (crop if SCALE == 1.0 else cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)), nb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("E:/NailIQ_data/raw/hb_skin_nails_figshare"))
    ap.add_argument("--out", type=Path, default=REPO / "ml" / "eval" / "hb_nails_scan.json")
    ap.add_argument("--assisted", action="store_true", help="send the dataset nail box as top_nail_bbox")
    args = ap.parse_args()
    app_module, _ = create_eval_client()
    app_module._rate_limited = lambda ip: False
    with app_module.app.app_context():
        app_module.db.create_all()
    client = app_module.app.test_client()
    side = enc(np.full((64, 64, 3), 128, np.uint8))
    rows = list(csv.DictReader(open(args.root / "metadata.csv")))
    cnt = defaultdict(Counter); anyflag = 0; n = 0; allabst = 0; flagged = []
    for r in rows:
        img = cv2.imread(str(args.root / "photo" / f"{r['PATIENT_ID']}.jpg"))
        if img is None:
            continue
        for k, box in enumerate(ast.literal_eval(r["NAIL_BOUNDING_BOXES"])):
            crop, nb = window(img, box)
            payload = {"side_image": side, "top_image": enc(crop)}
            if args.assisted and nb[2] > nb[0] and nb[3] > nb[1]:
                payload["top_nail_bbox"] = nb          # the app's nail-box selection, here from the dataset's own box
            resp = client.post("/analyze", json=payload)
            if resp.status_code != 200:
                raise SystemExit(f"HTTP {resp.status_code} patient {r['PATIENT_ID']}")
            fs = [f for f in resp.get_json()["findings"] if f["label"] not in ("clubbing", "pallor")]
            n += 1
            out = [f["label"] for f in fs if f["verdict"] == "outside"]
            for f in fs:
                cnt[f["label"]][f["verdict"] if f["verdict"] != "inconclusive" else "inc:" + str(f.get("failure_reason"))] += 1
            if all(f["verdict"] == "inconclusive" for f in fs):
                allabst += 1
            if out:
                anyflag += 1; flagged.append({"patient": r["PATIENT_ID"], "nail": k, "hb": r["HB_LEVEL_GperL"], "flags": out})
        if n % 150 < 3:
            print(f"  {n} nails", flush=True)
    print(f"\nnails scanned: {n}; every condition abstained: {allabst}; at least one visible flag: {anyflag} ({anyflag / n:.1%})")
    summary = {}
    for c in sorted(cnt):
        o = cnt[c]["outside"]; inc = sum(v for k, v in cnt[c].items() if k.startswith("inc:"))
        summary[c] = {"outside": o, "within": cnt[c]["within"], "inconclusive": inc, "fp_of_all": round(o / n, 3)}
        print(f"  {c:22s} outside {o:4d} ({o / n:5.1%})  within {cnt[c]['within']:4d}  inconclusive {inc}")
    json.dump({"n": n, "all_abstained": allabst, "any_flag": anyflag, "per_condition": summary, "flagged": flagged},
              open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
