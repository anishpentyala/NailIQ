"""Cache per-crop features for the 'new methods' experiments (2026-10-20).

For every crop in data/raw/onych_app_crops (all classes except pallor) store
  dino : frozen DINOv2 ViT-B/14 features (CLS + mean patch token, averaged over the image and its flips/quarter-turns)
  prof : rotation-invariant hand-built colour-profile features (Lab profiles along both nail axes, banding, white fraction)
  meta : path / src / split / cls
Output: C:/NailIQ_recovery/features/sign_features.npz (+ meta json). Run from repo root with ml/venv.
"""
import json, sys
from pathlib import Path

import cv2, numpy as np, torch

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "data" / "raw" / "onych_app_crops"
OUT = Path("C:/NailIQ_recovery/features"); OUT.mkdir(parents=True, exist_ok=True)
SKIP = {"pallor"}
S = 112  # profile resolution


def list_items():
    items = []
    for sp in ("train", "valid", "test"):
        for d in sorted((ROOT / sp).glob("*")):
            if not d.is_dir() or d.name in SKIP:
                continue
            for f in sorted(d.glob("*.png")):
                items.append(dict(p=str(f), src=f.name.split("__")[0], split=sp, cls=d.name))
    return items


def _canon(v):
    """Direction-free: flip so the brighter half comes first (v is a 1-D profile of L)."""
    h = len(v) // 2
    return v if v[:h].mean() >= v[h:].mean() else v[::-1]


def profile_features(bgr):
    im = cv2.resize(bgr, (S, S), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[..., 1:] -= 128.0
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    feats = []
    # global colour stats
    for ch in (L, A, B):
        feats += [ch.mean(), ch.std(), *np.percentile(ch, [5, 25, 50, 75, 95])]
    white = ((L > 190) & (np.hypot(A, B) < 18)).mean()
    dark = (L < 70).mean()
    feats += [white, dark, ((L > 170) & (np.hypot(A, B) < 25)).mean()]
    # profiles along each axis (rows / cols), canonicalised, binned to 10
    axes = []
    for ax in (0, 1):
        pL = L.mean(ax); pA = A.mean(ax); pB = B.mean(ax)
        flip = _canon(pL) is not pL
        pL, pA, pB = (p[::-1] if flip else p for p in (pL, pA, pB))
        nb = 10
        binned = [np.array([c.mean() for c in np.array_split(p, nb)]) for p in (pL, pA, pB)]
        hp = pL - cv2.GaussianBlur(pL.reshape(1, -1), (0, 0), 6).ravel()
        # banding: number and prominence of peaks/troughs in the high-passed profile
        peaks = int(((hp[1:-1] > hp[:-2]) & (hp[1:-1] > hp[2:]) & (hp[1:-1] > 4)).sum())
        troughs = int(((hp[1:-1] < hp[:-2]) & (hp[1:-1] < hp[2:]) & (hp[1:-1] < -4)).sum())
        e = float(np.abs(hp).mean())
        axes.append((float(pL.std()), np.concatenate(binned), [peaks, troughs, e, float(pL[: S // 2].mean() - pL[S // 2:].mean())]))
    axes.sort(key=lambda t: -t[0])   # most-varying axis first => invariant to quarter turns
    for sd, binned, extra in axes:
        feats += [sd, *binned, *extra]
    return np.array(feats, np.float32)


def main():
    items = list_items()
    print(len(items), "crops", flush=True)
    import timm
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = timm.create_model("vit_base_patch14_dinov2.lvd142m", pretrained=True, num_classes=0, img_size=224).to(dev).eval().half()
    mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)
    dino, prof = [], []
    B = 32
    for i in range(0, len(items), B):
        batch = items[i:i + B]
        ims = [cv2.imread(it["p"]) for it in batch]
        prof += [profile_features(im) for im in ims]
        x = np.stack([cv2.cvtColor(cv2.resize(im, (224, 224), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB) for im in ims])
        x = torch.from_numpy(x).to(dev).permute(0, 3, 1, 2).float() / 255.0
        x = ((x - mean) / std).half()
        with torch.no_grad():
            acc = 0
            for k in range(4):                       # quarter-turns (tip direction is arbitrary)
                for fl in (False, True):
                    xx = torch.rot90(x, k, (2, 3))
                    xx = torch.flip(xx, (3,)) if fl else xx
                    tok = m.forward_features(xx)      # (b, 1+n, 768)
                    acc = acc + torch.cat([tok[:, 0], tok[:, 1:].mean(1)], 1).float()
            dino.append((acc / 8).cpu().numpy())
        if (i // B) % 20 == 0:
            print(f"  {i}/{len(items)}", flush=True)
    np.savez_compressed(OUT / "sign_features.npz", dino=np.concatenate(dino), prof=np.stack(prof))
    json.dump(items, open(OUT / "sign_features_meta.json", "w"))
    print("saved", flush=True)


if __name__ == "__main__":
    main()
