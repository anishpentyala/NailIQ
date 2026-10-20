"""Leave-one-source-out lab for cached-feature classifiers (methods 2/3 and the synthetic-positive method 1).

Same protocol as scripts/train_sign_specialist.py: for each held-out source that has positives of the target,
train on the other sources (all their positives + train-split negatives), cutoff = 97th percentile of the other
sources' VALID healthy scores, evaluate on the held-out source's positives (every split) and healthy (every split)
plus the other sources' TEST healthy; eval images within dHash <= 5 of a training image are dropped.
Pooled = every fold's held-out positives/healthy scored with that fold's own cutoff.

Run: ml/venv/Scripts/python.exe scripts/sign_lab.py --target terrys_nails --feat both --clf lr
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

FEAT = Path("C:/NailIQ_recovery/features")
sys.path.insert(0, str(Path(__file__).resolve().parent))


def load(extra=None):
    z = np.load(FEAT / "sign_features.npz")
    meta = json.load(open(FEAT / "sign_features_meta.json"))
    H = np.load(FEAT / "sign_dhash.npy")
    X = {"dino": z["dino"], "prof": z["prof"]}
    return X, meta, H


def make_clf(kind, C):
    if kind == "lr":
        return make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight="balanced", max_iter=3000))
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.06, max_iter=250, class_weight="balanced", random_state=0)


def feats(X, kind):
    return np.concatenate([X["prof"], X["dino"]], 1) if kind == "both" else X[kind]


def rate(p, thr):
    return float((np.asarray(p) >= thr).mean()) if len(p) else float("nan")


def run(target, featkind, clf, C, syn=None, syn_neg=True, verbose=True, q=0.97):
    X, meta, H = load()
    F = feats(X, featkind)
    cls = np.array([m["cls"] for m in meta]); src = np.array([m["src"] for m in meta]); sp = np.array([m["split"] for m in meta])
    y = (cls == target).astype(int)
    is_h = cls == "healthy"
    pos_src = sorted(set(src[y == 1]))
    folds, pooled_p, pooled_h = {}, [], []
    for held in pos_src:
        tr = np.where((src != held) & ((y == 1) | (sp == "train")))[0]
        cal = np.where((src != held) & is_h & (sp == "valid"))[0]
        evp = np.where((src == held) & (y == 1))[0]
        evh = np.where(is_h & ((src == held) | ((src != held) & (sp == "test"))))[0]
        Htr = H[tr]
        keep = lambda idx: np.array([i for i in idx if not ((Htr != H[i]).sum(1) <= 5).any()], int)   # noqa: E731
        cal, evp, evh = keep(cal), keep(evp), keep(evh)
        Ftr, ytr = F[tr], y[tr]
        if syn is not None:
            ok = syn["base_src"] != held                     # never use synthetics built from the held-out source's healthy crops
            Fs = feats({"dino": syn["dino"], "prof": syn["prof"]}, featkind)[ok]
            ys = (syn["sign"][ok] == target).astype(int)
            if not syn_neg:
                Fs, ys = Fs[ys == 1], ys[ys == 1]
            Ftr = np.concatenate([Ftr, Fs]); ytr = np.concatenate([ytr, ys])
        m = make_clf(clf, C).fit(Ftr, ytr)
        s = lambda idx: m.predict_proba(F[idx])[:, 1]   # noqa: E731
        pc, pp, ph = s(cal), s(evp), s(evh)
        thr = float(np.quantile(pc, q))
        auc = roc_auc_score(np.r_[np.ones(len(pp)), np.zeros(len(ph))], np.r_[pp, ph]) if len(pp) and len(ph) else None
        orc = rate(pp, float(np.quantile(ph, 0.95))) if len(ph) else None
        folds[held] = dict(n_pos=len(pp), n_h=len(ph), recall=round(rate(pp, thr), 3), fp=round(rate(ph, thr), 3),
                           auc=round(auc, 3) if auc else None, oracle5=round(orc, 3) if orc is not None else None)
        pooled_p += [(p >= thr) for p in pp]; pooled_h += [(p >= thr) for p in ph]
    pooled = dict(recall=round(float(np.mean(pooled_p)), 3), fp=round(float(np.mean(pooled_h)), 3),
                  n_pos=len(pooled_p), n_h=len(pooled_h))
    if verbose:
        print(f"{target} feat={featkind} clf={clf} C={C} syn={'yes' if syn is not None else 'no'}")
        for h, r in folds.items():
            print("  held", h, r)
        print("  POOLED", pooled, flush=True)
    return folds, pooled


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--feat", default="both", choices=["prof", "dino", "both"])
    ap.add_argument("--clf", default="lr", choices=["lr", "hgb"])
    ap.add_argument("--C", type=float, default=0.05)
    ap.add_argument("--syn", action="store_true", help="add synthetic positives (and other-sign synthetics as negatives)")
    ap.add_argument("--no-syn-neg", action="store_true")
    ap.add_argument("--q", type=float, default=0.97)
    a = ap.parse_args()
    syn = dict(np.load(FEAT / "synthetic.npz")) if a.syn else None
    run(a.target, a.feat, a.clf, a.C, syn, not a.no_syn_neg, True, a.q)
