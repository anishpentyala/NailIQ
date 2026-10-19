"""Generic EfficientNet-B0 specialist for a sign whose positives live in the app-style crop cache.

Reads data/raw/onych_app_crops/<split>/<class>/<src>__*.png (built by build_onycholysis_app_crops.py and
build_new_sign_crops.py). Class dirs: <target> (y=1), healthy (y=0), and every other disease dir (y=0, "other",
trained against so the model does not just learn "any abnormal nail").
  --folds han,nihati   leave-one-source-out: train on the other sources' positives (+ all negatives' train split),
                       score the held-out source's positives and healthy (plus the other sources' healthy test split)
  --final              train on every source's train split, cutoff = 97th pct of valid healthy, report test, save
                       ml/models/<target>_specialist.{pt,json}
Eval images within dHash <= 5 of a training image are dropped.

Run from repo root: ml/venv/Scripts/python.exe scripts/train_sign_specialist.py --target onychomycosis --folds han,nihati
"""
import argparse, json, sys
from pathlib import Path

import numpy as np, torch
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_onycholysis_specialist as T  # noqa: E402

ROOT = Path("data/raw/onych_app_crops")
OTHERS = ("onycholysis", "melanonychia", "leukonychia", "terrys_nails", "clubbing", "beaus_lines", "muehrckes_lines", "onychomycosis", "psoriasis", "naildystrophy")


def collect(target):
    items = []
    for sp in ("train", "valid", "test"):
        for d in sorted((ROOT / sp).glob("*")):
            if not d.is_dir() or d.name not in (target, "healthy") + OTHERS:
                continue
            kind = "pos" if d.name == target else "healthy" if d.name == "healthy" else "other"
            for f in d.glob("*.png"):
                items.append(dict(p=f, src=f.name.split("__")[0], split=sp, y=int(kind == "pos"), kind=kind, cls=d.name))
    for it in items:
        it["x"] = T.load(it["p"]); it["h"] = T.dhash(it["x"])
    return items


def clean(L, Htr):
    return [i for i in L if not ((Htr != i["h"]).sum(1) <= 5).any()]


def stats(pp, ph, thr):
    yy = np.r_[np.ones(len(pp)), np.zeros(len(ph))]
    return {"n_pos": len(pp), "n_healthy": len(ph), "recall": round(T.rate(pp, thr), 3), "healthy_fp": round(T.rate(ph, thr), 3),
            "auc": round(float(roc_auc_score(yy, np.r_[pp, ph])), 3) if len(pp) and len(ph) else None,
            "oracle_recall_at_5pct_fp": round(T.rate(pp, float(np.quantile(ph, 0.95))), 3) if len(ph) else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--folds", default="")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    name = f"{a.target}_specialist"
    items = collect(a.target)
    pos_src = sorted({i["src"] for i in items if i["y"] == 1})
    print("loaded", len(items), "positives by source", {s: sum(1 for i in items if i["y"] == 1 and i["src"] == s) for s in pos_src}, flush=True)
    sc = lambda ms, L: np.mean([T.predict(m, L) for m in ms], 0)  # noqa: E731
    report = {}
    for held in [h for h in a.folds.split(",") if h]:
        tr = [i for i in items if i["src"] != held and (i["y"] == 1 or i["split"] == "train")]
        Htr = np.stack([i["h"] for i in tr])
        cal_h = clean([i for i in items if i["src"] != held and i["kind"] == "healthy" and i["split"] == "valid"], Htr)
        ev_pos = clean([i for i in items if i["src"] == held and i["y"] == 1], Htr)
        ev_h = clean([i for i in items if i["kind"] == "healthy" and (i["src"] == held or (i["src"] != held and i["split"] == "test"))], Htr)
        ev_o = clean([i for i in items if i["kind"] == "other" and i["split"] in ("valid", "test")], Htr)
        print(f"fold hold-out {held}: train {len(tr)} (pos {sum(i['y'] for i in tr)}), cal healthy {len(cal_h)}, eval pos {len(ev_pos)}, eval healthy {len(ev_h)}", flush=True)
        ms = [T.train(tr, a.epochs, s) for s in range(a.seeds)]
        pc, pp, ph, po = sc(ms, cal_h), sc(ms, ev_pos), sc(ms, ev_h), sc(ms, ev_o)
        thr = float(np.quantile(pc, 0.97))
        r = {"threshold": round(thr, 4), **stats(pp, ph, thr), "other_disease_flag_rate": round(T.rate(po, thr), 3), "n_other": len(po),
             "healthy_by_source": {s: round(T.rate(np.array([p for p, i in zip(ph, ev_h) if i["src"] == s]), thr), 3) for s in {i["src"] for i in ev_h}}}
        print(held, json.dumps(r), flush=True)
        report[held] = r
        torch.save([m.state_dict() for m in ms], f"ml/models/{name}__{a.tag}heldout_{held}.pt")
        json.dump(r, open(f"ml/eval/{name}_{a.tag}{held}.json", "w"), indent=2)
    if a.final:
        tr = [i for i in items if i["split"] == "train"]
        Htr = np.stack([i["h"] for i in tr])
        n_p0 = sum(1 for i in items if i["y"] == 1 and i["split"] != "train")
        n_h0 = sum(1 for i in items if i["kind"] == "healthy" and i["split"] != "train")
        cal_h = clean([i for i in items if i["kind"] == "healthy" and i["split"] == "valid"], Htr)
        cal_p = clean([i for i in items if i["y"] == 1 and i["split"] == "valid"], Htr)
        te_p = clean([i for i in items if i["y"] == 1 and i["split"] == "test"], Htr)
        te_h = clean([i for i in items if i["kind"] == "healthy" and i["split"] == "test"], Htr)
        print("near-duplicates of training images dropped from valid/test (pos, healthy):",
              n_p0 - len(cal_p) - len(te_p), n_h0 - len(cal_h) - len(te_h), flush=True)
        print(f"final: train {len(tr)} (pos {sum(i['y'] for i in tr)}), valid pos {len(cal_p)} healthy {len(cal_h)}, test pos {len(te_p)} healthy {len(te_h)}", flush=True)
        ms = [T.train(tr, a.epochs, s) for s in range(a.seeds)]
        torch.save({"state_dicts": [m.state_dict() for m in ms], "backbone": "efficientnet_b0", "size": T.SZ}, f"ml/models/{name}.pt")
        pc, pvp, ptp, pth = sc(ms, cal_h), sc(ms, cal_p), sc(ms, te_p), sc(ms, te_h)
        thr = float(np.quantile(pc, 0.97))
        r = {"threshold": round(thr, 4), "backbone": "efficientnet_b0", "valid": stats(pvp, pc, thr), "test": stats(ptp, pth, thr),
             "test_by_source_recall": {s: round(T.rate(np.array([p for p, i in zip(ptp, te_p) if i["src"] == s]), thr), 3) for s in {i["src"] for i in te_p}},
             "test_healthy_fp_by_source": {s: round(T.rate(np.array([p for p, i in zip(pth, te_h) if i["src"] == s]), thr), 3) for s in {i["src"] for i in te_h}}}
        print("final", json.dumps(r), flush=True)
        json.dump(r, open(f"ml/models/{name}.json", "w"), indent=2)


if __name__ == "__main__":
    main()
