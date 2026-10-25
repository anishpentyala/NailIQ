"""Fine-tuned per-sign AI specialists on the top-down nail crop (onycholysis, leukonychia, melanonychia).

For these signs the classical heuristic is near-chance and the shared color CNN stays under the
low-sample guard, so each has a dedicated EfficientNet-B0 trained by
scripts/train_onycholysis_specialist.py (`--target <sign>`) on the app's own crops (the same
nail_locator + compute_nail_region front end `pipeline.analyze_top_color` uses) plus the Han
clinical set. Weights + the validation-picked cutoff live in ml/models/<sign>_specialist.{pt,json}
(gitignored; see CLAUDE.md for the regeneration commands). `apply` swaps a specialist's call in for
that sign's finding, and leaves the finding untouched when the weights or torch are absent.

ENABLED is a deliberate allowlist: a sign only gets a specialist verdict once it has cleared the
validation bar (see validation_policy.py). melanonychia was held back until darker-skin healthy
nails (Ghana) were added as negatives; its evidence is still a single positive source, so the skin-tone
caveat in skin_tone.apply_coverage matters for it.

Lazy + optional like classifier.py: the Flask app never hard-depends on torch.
"""

import importlib.util
import json
import os
from pathlib import Path

import cv2
import numpy as np

from . import color_classifier, onnx_backend

ENABLED = ("onycholysis", "leukonychia", "beaus_lines")  # melanonychia withheld 2026-10-18 (real-phone false alarm). beaus_lines (2026-10-19) is a LIMITED-validation sign, see validation_policy.LIMITED_VALIDATION. muehrckes_lines was tried 2026-10-20 and reverted: flags 20/43 (46.5%) readable real-camera Hb nails
_MODELS = Path(__file__).resolve().parent.parent / "models"
_cache = {}


def _paths(sign):
    return _MODELS / f"{sign}_specialist.pt", _MODELS / f"{sign}_specialist.json"


def is_available(sign):
    weights, meta = _paths(sign)
    if onnx_backend.active():
        return sign in ENABLED and meta.is_file() and onnx_backend.has(f"{sign}_specialist_0.onnx")
    return sign in ENABLED and weights.is_file() and meta.is_file() and importlib.util.find_spec("torch") is not None


def threshold(sign):
    return float(json.loads(_paths(sign)[1].read_text())["threshold"])


def _load(sign):
    if sign not in _cache:
        import torch
        import torch.nn as nn
        from torchvision import models
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        blob = torch.load(_paths(sign)[0], map_location="cpu")
        nets = []
        for sd in blob["state_dicts"]:
            m = models.efficientnet_b0(weights=None)
            m.classifier[1] = nn.Linear(m.classifier[1].in_features, 1)
            m.load_state_dict(sd)
            nets.append(m.to(dev).eval())
        _cache[sign] = (torch, dev, nets, blob.get("size", 224))
    return _cache[sign]


def probability(sign, nail_bgr):
    """Mean sigmoid over members x 4 quarter-turns x flip (tip direction is irrelevant)."""
    if onnx_backend.active():
        return _probability_onnx(sign, nail_bgr)
    torch, dev, nets, size = _load(sign)
    rgb = cv2.cvtColor(cv2.resize(nail_bgr, (size, size)), cv2.COLOR_BGR2RGB)
    mean = torch.tensor([0.485, 0.456, 0.406], device=dev)[:, None, None]
    std = torch.tensor([0.229, 0.224, 0.225], device=dev)[:, None, None]
    x = (torch.from_numpy(np.ascontiguousarray(rgb)).to(dev).permute(2, 0, 1).float()[None] / 255 - mean) / std
    total, n = 0.0, 0
    with torch.no_grad():
        for net in nets:
            for k in range(4):
                for flip in (False, True):
                    xx = torch.rot90(x, k, (2, 3))
                    xx = torch.flip(xx, (3,)) if flip else xx
                    total += torch.sigmoid(net(xx)).item()
                    n += 1
    return total / n


def _probability_onnx(sign, nail_bgr):
    """Same average as the PyTorch path: sigmoid over members x 4 quarter-turns x flip, in numpy + ONNX."""
    size = int(json.loads(_paths(sign)[1].read_text()).get("size", 224))
    rgb = cv2.cvtColor(cv2.resize(nail_bgr, (size, size)), cv2.COLOR_BGR2RGB)
    x = onnx_backend.preprocess(rgb, size, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225], resize=None)
    views = []
    for k in range(4):
        r = np.rot90(x, k, axes=(1, 2))
        views.extend([r, r[:, :, ::-1]])
    batch = np.stack(views)
    total, n, i = 0.0, 0, 0
    while onnx_backend.has(f"{sign}_specialist_{i}.onnx"):
        logits = onnx_backend.run(f"{sign}_specialist_{i}.onnx", batch).reshape(-1)
        total += float((1.0 / (1.0 + np.exp(-logits))).sum())
        n += len(logits)
        i += 1
    return total / n


def _finding(sign, prev, p, thr):
    outside = p >= thr
    span = max(thr, 1.0 - thr)
    return {
        "label": sign,
        "display_name": prev["display_name"],
        "value": None,
        "unit": None,
        "verdict": "outside" if outside else "within",
        # heuristic, capped: a model score is not a calibrated probability
        "confidence": round(min(0.9, 0.5 + 0.4 * abs(p - thr) / span), 2),
        "track_used": "color_fused",
        "agreement": "ml_only",
        "failure_reason": None,
        "color": {"verdict": prev.get("verdict"), "confidence": prev.get("confidence")},
        "ml": {"predicted_label": sign if outside else "healthy", "confidence": round(p, 3)},
    }


def apply(findings, image_bgr, bbox_norm):
    """Replace each enabled sign's finding with its specialist's call; pass everything else through."""
    if bbox_norm is None or os.environ.get("NAILIQ_DISABLE_SPECIALISTS"):
        return findings  # the env switch lets color-CNN evals isolate the shared model
    signs = [s for s in ENABLED if is_available(s) and any(f["label"] == s for f in findings)]
    if not signs:
        return findings
    nail = color_classifier._crop_to_bbox(image_bgr, bbox_norm)
    if nail is None or nail.size == 0:
        return findings
    calls = {s: (probability(s, nail), threshold(s)) for s in signs}
    return [_finding(f["label"], f, *calls[f["label"]]) if f["label"] in calls else f for f in findings]
