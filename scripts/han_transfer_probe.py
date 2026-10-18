"""Does a sign learned from Han transfer to OTHER sources?

Per sign (melanonychia, onycholysis, leukonychia): logistic regression on frozen ImageNet
ResNet50 features (averaged over the 4 quarter-turns, so it is orientation-invariant) trained
on Han visible-sign crops vs Han healthy. The decision threshold is picked from out-of-fold
predictions on Han so that Han healthy false positives are ~3%. The model is then scored,
unchanged, on positives and healthy crops from sources it never saw (Arthitaya, NIHATI, KNM,
chaa; read from data/raw/goal60_authorized_cls, all splits). Ghana healthy are masked
featureless patches, reported separately and excluded from the FP headline.

This is a development probe: independent sources are labeled by their own (noisy)
classification labels, crops are tight nail crops, and nothing here is a phone-photo result.

Run from repo root with ml/venv:  ml/venv/Scripts/python.exe scripts/han_transfer_probe.py
"""
import csv, json, os
from pathlib import Path

import cv2, numpy as np, torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from torchvision import models

HAN = Path("data/raw/han_canon")
IND = Path("data/raw/goal60_authorized_cls")
SIGNS = ["melanonychia", "onycholysis", "leukonychia"]
TARGET_FP = 0.03
dev = "cuda" if torch.cuda.is_available() else "cpu"
net = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
net.fc = torch.nn.Identity()
net = net.to(dev).eval()
MEAN = torch.tensor([0.485, 0.456, 0.406], device=dev)[:, None, None]
STD = torch.tensor([0.229, 0.224, 0.225], device=dev)[:, None, None]


@torch.no_grad()
def feats(paths, bs=64):
    out = []
    for i in range(0, len(paths), bs):
        ims = []
        for p in paths[i:i + bs]:
            im = cv2.imread(str(p))
            im = np.zeros((224, 224, 3), np.uint8) if im is None else im
            ims.append(cv2.cvtColor(cv2.resize(im, (224, 224)), cv2.COLOR_BGR2RGB))
        x = torch.from_numpy(np.stack(ims)).to(dev).permute(0, 3, 1, 2).float() / 255
        x = (x - MEAN) / STD
        out.append((sum(net(torch.rot90(x, k, (2, 3))) for k in range(4)) / 4).cpu().numpy())
    return np.concatenate(out)


def han_rows():
    rows = list(csv.reader(open(HAN / "manifest.csv")))[1:]
    excl = set(json.load(open(HAN / "exclusions.json")))
    out = []
    for path, split, cls, *_ in rows:
        rel = path.replace("\\", "/").split("han_canon/")[-1]
        if rel in excl:
            continue
        out.append((HAN / rel, split, cls))
    return out


def ind_rows():
    out = []
    for sp in ("train", "valid", "test"):
        for d in (IND / sp).iterdir():
            for f in d.iterdir():
                out.append((f, d.name, f.name.split("__")[0]))
    return out


def rate(p, thr):
    return float((p >= thr).mean()) if len(p) else float("nan")


def main():
    han = han_rows()
    ind = ind_rows()
    print(f"han crops {len(han)}, independent crops {len(ind)}", flush=True)
    hf = feats([r[0] for r in han])
    hcls = np.array([r[2] for r in han]); hsplit = np.array([r[1] for r in han])
    cache = {}

    def ind_feats(sel):
        key = tuple(sel)
        return feats([ind[i][0] for i in sel])

    healthy_idx = {src: [i for i, r in enumerate(ind) if r[1] == "healthy" and r[2] == src]
                   for src in ("knm", "chaa", "nihati", "arthitaya", "ghana")}
    real_healthy = [i for s in ("knm", "chaa", "nihati", "arthitaya") for i in healthy_idx[s]]
    hfe = {s: ind_feats(ix) for s, ix in healthy_idx.items()}
    real_h = np.concatenate([hfe[s] for s in ("knm", "chaa", "nihati", "arthitaya")])
    report = {}
    for sign in SIGNS:
        pos = (hcls == sign) & (hsplit != "test")
        neg = (hcls == "healthy") & (hsplit != "test")
        X = np.concatenate([hf[pos], hf[neg]]); y = np.r_[np.ones(pos.sum()), np.zeros(neg.sum())]
        clf = LogisticRegression(C=0.5, max_iter=3000, class_weight="balanced")
        oof = cross_val_predict(clf, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
        thr = float(np.quantile(oof[y == 0], 1 - TARGET_FP))
        clf.fit(X, y)
        r = {"train_pos": int(pos.sum()), "train_healthy": int(neg.sum()), "threshold": round(thr, 3),
             "han_oof_auc": round(float(roc_auc_score(y, oof)), 3)}
        tp = (hcls == sign) & (hsplit == "test"); th = (hcls == "healthy") & (hsplit == "test")
        if tp.sum():
            r["han_test"] = {"pos": int(tp.sum()), "recall": round(rate(clf.predict_proba(hf[tp])[:, 1], thr), 3),
                             "healthy_fp": round(rate(clf.predict_proba(hf[th])[:, 1], thr), 3)}
        pi = [i for i, q in enumerate(ind) if q[1] == sign]
        pf = ind_feats(pi); pp = clf.predict_proba(pf)[:, 1]
        hp = clf.predict_proba(real_h)[:, 1]
        yy = np.r_[np.ones(len(pp)), np.zeros(len(hp))]
        r["independent"] = {
            "pos": len(pp),
            "pos_by_source": {s: int(sum(1 for i in pi if ind[i][2] == s)) for s in set(ind[i][2] for i in pi)},
            "recall": round(rate(pp, thr), 3),
            "recall_by_source": {s: round(rate(np.array([pp[k] for k, i in enumerate(pi) if ind[i][2] == s]), thr), 3)
                                 for s in set(ind[i][2] for i in pi)},
            "real_healthy_n": len(hp), "real_healthy_fp": round(rate(hp, thr), 3),
            "ghana_healthy_fp": round(rate(clf.predict_proba(hfe["ghana"])[:, 1], thr), 3),
            "auc_vs_real_healthy": round(float(roc_auc_score(yy, np.r_[pp, hp])), 3)}
        report[sign] = r
        print(sign, json.dumps(r), flush=True)
    json.dump(report, open("ml/eval/han_transfer_probe.json", "w"), indent=2)


if __name__ == "__main__":
    main()
