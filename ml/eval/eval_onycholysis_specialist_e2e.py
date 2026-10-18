"""Onycholysis specialist on FULL source photos, through the production nail front end.

For each fold model (trained with one source held out; see scripts/train_onycholysis_specialist.py)
this reproduces pipeline.analyze_top_color's front half exactly -- realistic-framing b64 (480px + gray
border), blur gate, nail_locator proposal, roi_quality, contour, compute_nail_region -- then crops to the
nail bbox the way color_classifier does and scores the crop with the specialist (8-way TTA; the model
trains on random quarter-turns so tip direction is irrelevant).

Held-out source: every split. Other sources (KNM, chaa, the remaining independent source): TEST split only,
the same bucket logic the crop dataset used. Abstentions (no nail found / photo quality) count as misses
for positives and as non-flags for healthy, and are reported separately.

Run from repo root: ml/venv/Scripts/python.exe ml/eval/eval_onycholysis_specialist_e2e.py
"""
import base64, json, sys
from pathlib import Path

import cv2, numpy as np, torch, torch.nn as nn
from torchvision import models

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend"))

from ml.eval.eval_color_sensitivity import b64                      # noqa: E402
from ml.eval.eval_end_to_end import gather                           # noqa: E402
from ml.infer import color_classifier, image_quality, nail_locator, nail_region  # noqa: E402
from ml.infer.preprocessing import BLUR_THRESHOLD, decode_base64_image, extract_best_contour, focus_score, is_flat_frame  # noqa: E402

dev = "cuda" if torch.cuda.is_available() else "cpu"
MEAN = torch.tensor([0.485, 0.456, 0.406], device=dev)[:, None, None]
STD = torch.tensor([0.229, 0.224, 0.225], device=dev)[:, None, None]


def source_of(path):
    s = str(path).lower()
    for key, name in (("arthitaya", "arthitaya"), ("nihati", "nihati"), ("mxoqy", "knm"), ("ckvkd", "chaa"), ("ghana", "ghana")):
        if key in s:
            return name
    return "other"


def load_models(held):
    out = []
    for sd in torch.load(REPO / "ml" / "models" / f"onycholysis_specialist__heldout_{held}.pt", map_location="cpu"):
        m = models.efficientnet_b0(weights=None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
        m.load_state_dict(sd)
        out.append(m.to(dev).eval())
    return out


@torch.no_grad()
def score(ms, bgr):
    rgb = cv2.cvtColor(cv2.resize(bgr, (224, 224)), cv2.COLOR_BGR2RGB)
    x = torch.from_numpy(rgb).to(dev).permute(2, 0, 1).float()[None] / 255
    x = (x - MEAN) / STD
    p = 0
    for m in ms:
        for k in range(4):
            for fl in (False, True):
                xx = torch.rot90(x, k, (2, 3))
                xx = torch.flip(xx, (3,)) if fl else xx
                p = p + torch.sigmoid(m(xx)).item()
    return p / (8 * len(ms))


def front_end(path):
    """(nail_crop_bgr or None, reason). Mirrors pipeline.analyze_top_color before the classifiers."""
    raw = b64(path)
    if raw is None:
        return None, "unreadable"
    image = decode_base64_image(raw)
    if image is None:
        return None, "invalid_image"
    if is_flat_frame(image):
        return None, "camera_feed_blank"
    if focus_score(image) < BLUR_THRESHOLD:
        return None, "too_blurry"
    bbox = None
    proposals = nail_locator.detect(image)
    if proposals:
        bbox = proposals[0]["bbox"]
        reason = nail_locator.roi_quality(image, bbox)
        if reason:
            return None, reason
    contour, validation = extract_best_contour(image)
    if bbox is None and not validation["is_valid"]:
        return None, validation["reason"]
    if validation["is_valid"]:
        region, reason = (nail_region.compute_nail_region(image, contour, nail_bbox=bbox) if bbox is not None
                          else nail_region.compute_nail_region(image, contour))
        if region is None and bbox is None:
            return None, reason
        if region is not None and bbox is None:
            bbox = region.get("bbox_norm")
    if bbox is None:
        return None, "no_nail_bbox"
    crop = color_classifier._crop_to_bbox(image, bbox)
    return (crop, None) if crop is not None and crop.size else (None, "empty_crop")


def main():
    items = {}
    for sp in ("train", "valid", "test"):
        for p, labels in gather(sp, include_authorized=True).items():
            items[p] = (sp, labels)
    report = {}
    pooled = {"pos": [], "neg": []}
    for held, other in (("arthitaya", "nihati"), ("nihati", "arthitaya")):
        cfg = json.load(open(REPO / "ml" / "eval" / f"onycholysis_specialist_{held}.json"))
        thr = cfg["threshold"]
        ms = load_models(held)
        pos, neg = [], []
        for p, (sp, labels) in items.items():
            src = source_of(p)
            if src == "ghana" or (src != held and sp != "test"):
                continue
            if "onycholysis" in labels and src == held:
                pos.append(p)
            elif labels == {"healthy"}:
                neg.append(p)
        print(f"fold {held}: positives {len(pos)}, healthy {len(neg)}", flush=True)
        res = {"pos": [], "neg": []}
        for kind, paths in (("pos", pos), ("neg", neg)):
            for i, p in enumerate(paths):
                crop, reason = front_end(p)
                res[kind].append((source_of(p), None if crop is None else score(ms, crop), reason))
                if (i + 1) % 50 == 0:
                    print(f"  {kind} {i + 1}/{len(paths)}", flush=True)
        def stats(rows):
            n = len(rows); ab = sum(1 for r in rows if r[1] is None)
            flagged = sum(1 for r in rows if r[1] is not None and r[1] >= thr)
            return n, ab, flagged
        n, ab, fl = stats(res["pos"])
        hn, hab, hfl = stats(res["neg"])
        by_src = {}
        for s in {r[0] for r in res["neg"]}:
            sn, sab, sfl = stats([r for r in res["neg"] if r[0] == s])
            by_src[s] = {"n": sn, "abstain": sab, "fp": round(sfl / sn, 3)}
        r = {"threshold": thr, "n_pos": n, "pos_abstain": ab, "recall_strict": round(fl / n, 3),
             "recall_of_readable": round(fl / max(1, n - ab), 3), "n_healthy": hn, "healthy_abstain": hab,
             "healthy_fp": round(hfl / hn, 3), "healthy_fp_by_source": by_src,
             "abstain_reasons": sorted({r_[2] for r_ in res["pos"] + res["neg"] if r_[2]})}
        print(held, json.dumps(r), flush=True)
        report[held] = r
        pooled["pos"].append((fl, n)); pooled["neg"].append((hfl, hn))
    report["pooled"] = {"recall_strict": round(sum(a for a, _ in pooled["pos"]) / sum(b for _, b in pooled["pos"]), 3),
                        "healthy_fp": round(sum(a for a, _ in pooled["neg"]) / sum(b for _, b in pooled["neg"]), 3)}
    print("pooled", json.dumps(report["pooled"]), flush=True)
    json.dump(report, open(REPO / "ml" / "eval" / "onycholysis_specialist_e2e.json", "w"), indent=2)


if __name__ == "__main__":
    main()
