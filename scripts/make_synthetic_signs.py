"""Method 1 (2026-10-20): synthetic sign positives painted onto REAL healthy nail crops (train split only, no Ghana patches).

Signs: terrys_nails (proximal ground-glass white, thin distal band), muehrckes_lines (paired transverse white bands),
beaus_lines (thin transverse dark grooves). Each sign's synthetics are also usable as negatives for the others.
The nail axis is taken as the crop's longer dimension (random if ~square); direction random. Pattern strengths are
randomised. Output: C:/NailIQ_recovery/features/synthetic.npz (dino, prof, sign, base_src) and a contact sheet.

Real held-out positives are the only judge of whether this helps (scripts/sign_lab.py --syn).
Run: ml/venv/Scripts/python.exe scripts/make_synthetic_signs.py [--n 1200]
"""
import argparse, json, sys
from pathlib import Path

import cv2, numpy as np, torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_sign_features import profile_features, ROOT, OUT  # noqa: E402

SIGNS = ("terrys_nails", "muehrckes_lines", "beaus_lines")


def coords(h, w, rng):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    ys, xs = ys / max(h - 1, 1), xs / max(w - 1, 1)
    vertical = h > 1.1 * w or (w <= 1.1 * h and rng.random() < 0.5)
    t, u = (ys, xs * 2 - 1) if vertical else (xs, ys * 2 - 1)
    if rng.random() < 0.5:
        t = 1 - t
    return t, u


def soft_mask(t, u):
    r = ((t - 0.5) / 0.5) ** 2 + (u / 0.88) ** 2
    return np.clip((1.0 - r) / 0.25, 0, 1)


def blend(lab, alpha, target):
    return lab * (1 - alpha[..., None]) + np.asarray(target, np.float32).reshape(1, 1, 3) * alpha[..., None]


def white(rng):
    return [rng.uniform(205, 242), 128 + rng.uniform(-3, 3), 128 + rng.uniform(-3, 3)]


def paint(bgr, sign, rng):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    t, u = coords(h, w, rng)
    m = soft_mask(t, u)
    if sign == "terrys_nails":
        f = rng.uniform(0.55, 0.85); s = rng.uniform(0.02, 0.05)
        pat = 1 / (1 + np.exp(-(f - t) / s))
        lab = blend(lab, pat * m * rng.uniform(0.7, 0.95), white(rng))
    elif sign == "muehrckes_lines":
        k = int(rng.integers(1, 4)); centers = []
        while len(centers) < k:
            c = rng.uniform(0.2, 0.8)
            if all(abs(c - o) > 0.14 for o in centers):
                centers.append(c)
        hw = rng.uniform(0.03, 0.055)
        pat = np.max([np.exp(-(((t - c) / hw) ** 4)) for c in centers], 0)
        lab = blend(lab, pat * m * rng.uniform(0.6, 0.9), white(rng))
    elif sign == "beaus_lines":
        k = int(rng.integers(1, 3))
        pat = np.zeros_like(t)
        for _ in range(k):
            c = rng.uniform(0.25, 0.8); hw = rng.uniform(0.012, 0.03)
            pat = np.maximum(pat, np.exp(-(((t - c) / hw) ** 2)))
        pat = pat * m
        lab[..., 0] *= 1 - rng.uniform(0.15, 0.4) * pat
        lab[..., 1] += rng.uniform(0, 6) * pat
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=1200); ap.add_argument("--png-dir", type=Path, default=None); a = ap.parse_args()
    rng = np.random.default_rng(0)
    bases = [f for d in (ROOT / "train" / "healthy",) for f in sorted(d.glob("*.png")) if not f.name.startswith("ghana__")]
    print(len(bases), "healthy train bases", flush=True)
    if a.png_dir:
        for sg in SIGNS:
            (a.png_dir / sg).mkdir(parents=True, exist_ok=True)
            for i in range(a.n):
                f = bases[int(rng.integers(len(bases)))]
                im = cv2.imread(str(f))
                if im is None or min(im.shape[:2]) < 24:
                    continue
                cv2.imwrite(str(a.png_dir / sg / f"{f.name.split('__')[0]}__{i}.png"), paint(im, sg, rng))
        print("pngs saved", flush=True)
        return
    import timm
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = timm.create_model("vit_base_patch14_dinov2.lvd142m", pretrained=True, num_classes=0, img_size=224).to(dev).eval().half()
    mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1); std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)
    dino, prof, sign, base_src, sheet = [], [], [], [], {s: [] for s in SIGNS}
    for s in SIGNS:
        for i in range(a.n):
            f = bases[int(rng.integers(len(bases)))]
            im = cv2.imread(str(f))
            if im is None or min(im.shape[:2]) < 24:
                continue
            out = paint(im, s, rng)
            prof.append(profile_features(out)); sign.append(s); base_src.append(f.name.split("__")[0])
            x = cv2.cvtColor(cv2.resize(out, (224, 224), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
            dino.append(x)
            if len(sheet[s]) < 16:
                sheet[s].append(cv2.resize(out, (112, 112)))
    X = torch.from_numpy(np.stack(dino))
    feats = []
    for i in range(0, len(X), 32):
        x = X[i:i + 32].to(dev).permute(0, 3, 1, 2).float() / 255.0
        x = ((x - mean) / std).half()
        with torch.no_grad():
            acc = 0
            for k in range(4):
                for fl in (False, True):
                    xx = torch.rot90(x, k, (2, 3)); xx = torch.flip(xx, (3,)) if fl else xx
                    tok = m.forward_features(xx)
                    acc = acc + torch.cat([tok[:, 0], tok[:, 1:].mean(1)], 1).float()
            feats.append((acc / 8).cpu().numpy())
    np.savez_compressed(OUT / "synthetic.npz", dino=np.concatenate(feats), prof=np.stack(prof), sign=np.array(sign), base_src=np.array(base_src))
    rows = [np.concatenate(sheet[s][:8], 1) for s in SIGNS] + [np.concatenate(sheet[s][8:16], 1) for s in SIGNS]
    cv2.imwrite(str(OUT / "synthetic_sheet.png"), np.concatenate(rows, 0))
    print("saved", len(sign), flush=True)


if __name__ == "__main__":
    main()
