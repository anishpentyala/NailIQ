"""Score every Han crop for whether its labeled sign is actually visible.

Han's A1 labels come partly from chart diagnoses, so many crops show a normal-looking nail.
Haiku judged ~190 crops per class as Y (visible) / N / U (unsure) from contact sheets
(orient/visfilter/vis_<class>.json). This fits a logistic regression on frozen ImageNet
ResNet50 features (Y vs N, U dropped), reports 5-fold CV accuracy/AUC and precision at the
keep threshold, then scores every crop of that class and writes visible_signs.csv.

Run from repo root with ml/venv:  ml/venv/Scripts/python.exe scripts/filter_han_visible_signs.py
"""
import csv, json, sys
from pathlib import Path

import cv2, numpy as np, torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from torchvision import models

ROOT = Path("data/raw/han-onychomycosis-figshare")
VF = ROOT / "orient" / "visfilter"
KEEP_P = 0.7
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
            if im is None:
                im = np.zeros((224, 224, 3), np.uint8)
            ims.append(cv2.cvtColor(cv2.resize(im, (224, 224)), cv2.COLOR_BGR2RGB))
        x = torch.from_numpy(np.stack(ims)).to(dev).permute(0, 3, 1, 2).float() / 255
        x = (x - MEAN) / STD
        # average over the 4 quarter-turns: visibility does not depend on tip direction
        f = sum(net(torch.rot90(x, k, (2, 3))) for k in range(4)) / 4
        out.append(f.cpu().numpy())
    return np.concatenate(out)


def main():
    classes = tuple(sys.argv[1:]) or ("melanonychia", "onycholysis", "whitespot")
    base = json.load(open(VF / "meta.json"))
    meta = base + [m for c in classes if (VF / f"meta_{c}.json").exists() for m in json.load(open(VF / f"meta_{c}.json"))]
    rows = []
    for cls in classes:
        files = [f for m in meta if m["cls"] == cls for f in m["files"]]
        lab = json.load(open(VF / f"vis_{cls}.json"))
        idx = [int(k) for k, v in lab.items() if v in ("Y", "N")]
        y = np.array([1 if lab[str(i)] == "Y" else 0 for i in idx])
        X = feats([Path(files[i]) for i in idx])
        clf = LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced")
        pcv = cross_val_predict(clf, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
        kept = pcv >= KEEP_P
        prec = float(y[kept].mean()) if kept.any() else float("nan")
        print(f"{cls}: labeled {len(y)} (Y {int(y.sum())}) cv acc {((pcv >= .5) == y).mean():.3f} "
              f"auc {roc_auc_score(y, pcv):.3f} | at p>={KEEP_P}: keeps {int(kept.sum())}/{len(y)}, "
              f"precision {prec:.3f}, recall of Y {float(kept[y == 1].mean()):.3f}", flush=True)
        clf.fit(X, y)
        allp = sorted((ROOT / "crops" / cls).glob("*.png"))
        pa = clf.predict_proba(feats(allp))[:, 1]
        for p, s in zip(allp, pa):
            rows.append([str(p.relative_to(ROOT)).replace("\\", "/"), cls, f"{s:.4f}"])
        print(f"  scored {len(allp)} crops, {int((pa >= KEEP_P).sum())} at p>={KEEP_P}", flush=True)
    # merge: keep rows of classes not re-scored in this run
    old = list(csv.reader(open(ROOT / "visible_signs.csv")))[1:] if (ROOT / "visible_signs.csv").exists() else []
    rows = [r for r in old if r[1] not in classes] + rows
    with open(ROOT / "visible_signs.csv", "w", newline="") as f:
        csv.writer(f).writerows([["crop", "cls", "p_visible"], *rows])


if __name__ == "__main__":
    main()
