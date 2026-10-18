"""Fine-tuned onycholysis specialist, scored by leave-one-source-out.

Positives: Han onycholysis (visible-sign filtered, tip-down) + the OTHER independent source.
Negatives: Han healthy + real healthy (KNM/chaa/other source) train splits. Ghana healthy are
masked patches and are excluded from training, reported separately.
Fold A holds out Arthitaya, fold B holds out NIHATI: every positive and healthy image of the held-out
source, plus the test splits of the sources that were trained on, are scored by a model that never saw them.
Threshold: 97th percentile of REAL healthy valid-split scores (never the eval images). Also reports the
oracle recall at 5% FP on the eval healthy set, which shows capacity independent of calibration.
Eval images within dHash distance <=5 of any Han crop are dropped (Han->eval leakage).

Run from repo root: ml/venv/Scripts/python.exe scripts/train_onycholysis_specialist.py [--epochs 10 --seeds 2]
"""
import argparse, csv, json
from pathlib import Path

import cv2, numpy as np, torch, torch.nn as nn
from sklearn.metrics import roc_auc_score
from torchvision import models
from torchvision.transforms import v2

HAN = Path("data/raw/han_canon")
IND = Path("data/raw/goal60_authorized_cls")
SZ = 224
TARGET = "onycholysis"  # set from --target
NAME = "onycholysis_specialist"
dev = "cuda" if torch.cuda.is_available() else "cpu"
MEAN = torch.tensor([0.485, 0.456, 0.406], device=dev)[:, None, None]
STD = torch.tensor([0.229, 0.224, 0.225], device=dev)[:, None, None]


def load(p):
    im = cv2.imread(str(p))
    if im is None:
        im = np.zeros((SZ, SZ, 3), np.uint8)
    return cv2.cvtColor(cv2.resize(im, (SZ, SZ), interpolation=cv2.INTER_AREA if im.shape[0] > SZ else cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB)


def dhash(img):
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    s = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    return (s[:, 1:] > s[:, :-1]).flatten()


def collect():
    items = []  # dict(arr, src, split, y)  y: 1 onycholysis, 0 healthy
    excl = set(json.load(open(HAN / "exclusions.json")))
    han_rows = list(csv.reader(open(HAN / "manifest.csv")))[1:]
    # Han only helps when it has positives for the target; otherwise "Han" would just mean "healthy"
    use_han = any(r[2] == TARGET for r in han_rows)
    for path, split, cls, *_ in (han_rows if use_han else []):
        rel = path.replace("\\", "/").split("han_canon/")[-1]
        if rel in excl or cls not in (TARGET, "healthy"):
            continue
        items.append(dict(p=HAN / rel, src="han", split=split, y=int(cls == TARGET)))
    for sp in ("train", "valid", "test"):
        for cls in (TARGET, "healthy"):
            if not (IND / sp / cls).exists():
                continue
            for f in (IND / sp / cls).iterdir():
                items.append(dict(p=f, src=f.name.split("__")[0], split=sp, y=int(cls == TARGET)))
    for it in items:
        it["x"] = load(it["p"])
    return items


class Aug:
    def __init__(self):
        self.t = v2.Compose([
            v2.RandomResizedCrop(SZ, scale=(0.6, 1.0), ratio=(0.8, 1.25), antialias=True),
            v2.RandomHorizontalFlip(), v2.RandomVerticalFlip(),
            v2.RandomApply([v2.GaussianBlur(5, (0.1, 2.0))], p=0.4),
            v2.ColorJitter(0.3, 0.3, 0.3, 0.03),
            v2.RandomApply([v2.JPEG((30, 90))], p=0.4)])

    def __call__(self, arr):
        x = torch.from_numpy(np.rot90(arr, np.random.randint(4)).copy()).permute(2, 0, 1)
        return self.t(x)


def to_in(xb):
    return ((xb.float() / 255) - MEAN) / STD


def build():
    m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
    return m.to(dev)


def train(tr, epochs, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    aug = Aug()
    X = [i["x"] for i in tr]; Y = np.array([i["y"] for i in tr], np.float32)
    # balance by source-class so Han healthy does not dominate real healthy
    w = np.zeros(len(tr))
    for key in {(i["src"], i["y"]) for i in tr}:
        idx = [k for k, i in enumerate(tr) if (i["src"], i["y"]) == key]
        w[idx] = 1.0 / np.sqrt(len(idx))
    w[Y == 1] *= (w[Y == 0].sum() / w[Y == 1].sum())
    w = w / w.sum()
    m = build()
    opt = torch.optim.AdamW(m.parameters(), lr=2e-4, weight_decay=1e-2)
    steps_per = max(1, len(tr) // 64)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 2e-4, total_steps=epochs * steps_per)
    scaler = torch.amp.GradScaler()
    for ep in range(epochs):
        m.train(); tot = 0
        for _ in range(steps_per):
            idx = np.random.choice(len(tr), 64, p=w)
            xb = torch.stack([aug(X[k]) for k in idx]).to(dev)
            yb = torch.from_numpy(Y[idx]).to(dev)
            with torch.autocast("cuda", enabled=dev == "cuda"):
                loss = nn.functional.binary_cross_entropy_with_logits(m(to_in(xb)).squeeze(1), yb)
            opt.zero_grad(); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
            tot += loss.item()
        print(f"  ep{ep + 1}/{epochs} loss {tot / steps_per:.3f}", flush=True)
    return m.eval()


@torch.no_grad()
def predict(m, items, bs=128):
    out = []
    if not items:
        return np.zeros(0)
    for i in range(0, len(items), bs):
        x = torch.from_numpy(np.stack([it["x"] for it in items[i:i + bs]])).to(dev).permute(0, 3, 1, 2)
        x = to_in(x)
        p = 0
        for k in range(4):
            for fl in (False, True):
                xx = torch.rot90(x, k, (2, 3))
                xx = torch.flip(xx, (3,)) if fl else xx
                p = p + torch.sigmoid(m(xx).squeeze(1))
        out.append((p / 8).cpu().numpy())
    return np.concatenate(out)


def rate(p, thr):
    return float((p >= thr).mean()) if len(p) else float("nan")


def main():
    global IND, TARGET, NAME
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--only", default=None, help="hold out only this source (arthitaya|nihati)")
    ap.add_argument("--ind-root", default=str(IND), help="independent-source crops, <split>/<class>/<source>__*.ext")
    ap.add_argument("--extra-real", default="", help="comma list of extra healthy sources to train/calibrate/eval on (e.g. ghana)")
    ap.add_argument("--folds", default="arthitaya,nihati", help="comma list of sources to hold out, one fold each")
    ap.add_argument("--target", default="onycholysis", help="sign to train: onycholysis|melanonychia|leukonychia")
    ap.add_argument("--tag", default="", help="prefix for output files (e.g. app_)")
    ap.add_argument("--final", action="store_true", help="train on every source's train split, calibrate on valid, report test, save the shipping weights")
    a = ap.parse_args()
    IND = Path(a.ind_root)
    TARGET = a.target
    NAME = f"{a.target}_specialist"
    items = collect()
    print("loaded", len(items), "images", flush=True)
    han_h = [dhash(i["x"]) for i in items if i["src"] == "han"]
    H = np.stack(han_h) if han_h else None
    for i in items:
        i["dup"] = False
        if i["src"] != "han" and H is not None:
            i["dup"] = bool(((H != dhash(i["x"])).sum(1) <= 5).any())
    print("Han->eval near-dups dropped:", {s: sum(1 for i in items if i["dup"] and i["src"] == s) for s in ("arthitaya", "nihati", "knm", "chaa")}, flush=True)
    items = [i for i in items if not i["dup"]]

    if a.final:
        real = ("knm", "chaa", "nihati", "arthitaya") + tuple(x for x in a.extra_real.split(",") if x)
        tr = [i for i in items if (i["src"] == "han" and i["split"] == "train")
              or (i["src"] in real and i["split"] == "train")]
        cal_h = [i for i in items if i["src"] in real and i["y"] == 0 and i["split"] == "valid"]
        cal_p = [i for i in items if i["src"] in real and i["y"] == 1 and i["split"] == "valid"]
        te_p = [i for i in items if i["src"] in real and i["y"] == 1 and i["split"] == "test"]
        te_h = [i for i in items if i["src"] in real and i["y"] == 0 and i["split"] == "test"]
        print(f"final: train {len(tr)} (pos {sum(i['y'] for i in tr)}), valid pos {len(cal_p)} healthy {len(cal_h)}, "
              f"test pos {len(te_p)} healthy {len(te_h)}", flush=True)
        ms = [train(tr, a.epochs, s) for s in range(a.seeds)]
        torch.save({"state_dicts": [m.state_dict() for m in ms], "backbone": "efficientnet_b0", "size": SZ},
                   f"ml/models/{NAME}.pt")
        sc = lambda L: np.mean([predict(m, L) for m in ms], 0)
        pc, pvp, ptp, pth = sc(cal_h), sc(cal_p), sc(te_p), sc(te_h)
        thr = float(np.quantile(pc, 0.97))
        r = {"threshold": round(thr, 4), "backbone": "efficientnet_b0",
             "valid": {"n_pos": len(pvp), "recall": round(rate(pvp, thr), 3), "n_healthy": len(pc), "healthy_fp": round(rate(pc, thr), 3)},
             "test": {"n_pos": len(ptp), "recall": round(rate(ptp, thr), 3), "n_healthy": len(pth), "healthy_fp": round(rate(pth, thr), 3),
                      "healthy_fp_by_source": {s: round(rate(np.array([p for p, i in zip(pth, te_h) if i["src"] == s]), thr), 3)
                                               for s in {i["src"] for i in te_h}}}}
        print("final", json.dumps(r), flush=True)
        json.dump(r, open(f"ml/models/{NAME}.json", "w"), indent=2)
        return
    for i in items:
        i["h"] = dhash(i["x"])
    report = {}
    pooled = {"pos": [], "neg": [], "thr": []}
    for held in a.folds.split(","):
        if a.only and held != a.only:
            continue
        real = tuple(x for x in ("knm", "chaa", "nihati", "arthitaya") if x != held) + tuple(x for x in a.extra_real.split(",") if x)
        tr = [i for i in items if (i["src"] == "han" and i["split"] == "train")
              or (i["src"] in real and i["y"] == 1)
              or (i["src"] in real and i["y"] == 0 and i["split"] == "train")]
        cal_h = [i for i in items if i["src"] in real and i["y"] == 0 and i["split"] == "valid"]
        ev_pos = [i for i in items if i["src"] == held and i["y"] == 1]
        ev_h = [i for i in items if i["y"] == 0 and ((i["src"] == held) or (i["src"] in real and i["split"] == "test"))]
        if not ev_pos:
            print(f"hold-out {held}: no {TARGET} positives, skipped", flush=True)
            continue
        # cross-source leakage: drop calibration/eval images that near-duplicate a training image
        Htr = np.stack([i["h"] for i in tr])
        clean = lambda L: [i for i in L if not ((Htr != i["h"]).sum(1) <= 5).any()]
        n0 = (len(cal_h), len(ev_pos), len(ev_h))
        cal_h, ev_pos, ev_h = clean(cal_h), clean(ev_pos), clean(ev_h)
        print(f"  dropped near-duplicates of training images (cal healthy, eval pos, eval healthy): "
              f"{n0[0] - len(cal_h)}, {n0[1] - len(ev_pos)}, {n0[2] - len(ev_h)}", flush=True)
        ev_g = [i for i in items if i["src"] == "ghana" and i["y"] == 0 and i["split"] == "test"]
        print(f"fold hold-out {held}: train {len(tr)} (pos {sum(i['y'] for i in tr)}), cal healthy {len(cal_h)}, "
              f"eval pos {len(ev_pos)}, eval healthy {len(ev_h)}", flush=True)
        ms = [train(tr, a.epochs, s) for s in range(a.seeds)]
        torch.save([m.state_dict() for m in ms], f"ml/models/{NAME}__{a.tag}heldout_{held}.pt")
        sc = lambda L: np.mean([predict(m, L) for m in ms], 0)
        pc, pp, ph, pg = sc(cal_h), sc(ev_pos), sc(ev_h), sc(ev_g)
        thr = float(np.quantile(pc, 0.97))
        thr_oracle = float(np.quantile(ph, 0.95))
        yy = np.r_[np.ones(len(pp)), np.zeros(len(ph))]
        r = {"threshold": round(thr, 3), "n_pos": len(pp), "n_healthy": len(ph),
             "recall": round(rate(pp, thr), 3), "healthy_fp": round(rate(ph, thr), 3),
             "auc": round(float(roc_auc_score(yy, np.r_[pp, ph])), 3),
             "oracle_recall_at_5pct_fp": round(rate(pp, thr_oracle), 3),
             "ghana_fp": round(rate(pg, thr), 3), "cal_fp_check": round(rate(pc, thr), 3),
             "healthy_by_source_fp": {s: round(rate(np.array([p for p, i in zip(ph, ev_h) if i["src"] == s]), thr), 3)
                                      for s in {i["src"] for i in ev_h}}}
        print(held, json.dumps(r), flush=True)
        report[held] = r
        json.dump(r, open(f"ml/eval/{NAME}_{a.tag}{held}.json", "w"), indent=2)
        pooled["pos"].append(pp >= thr); pooled["neg"].append(ph >= thr)
    if len(pooled["pos"]) < 2:
        return
    pr = np.concatenate(pooled["pos"]); nr = np.concatenate(pooled["neg"])
    report["pooled"] = {"n_pos": int(len(pr)), "recall": round(float(pr.mean()), 3),
                        "n_healthy": int(len(nr)), "healthy_fp": round(float(nr.mean()), 3)}
    print("pooled", json.dumps(report["pooled"]), flush=True)
    json.dump(report, open(f"ml/eval/{NAME}_{a.tag}pooled.json", "w"), indent=2)


if __name__ == "__main__":
    main()
