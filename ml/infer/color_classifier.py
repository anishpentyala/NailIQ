"""Trained-CNN second opinion for the colour/texture track.

Companion to ml/train/train_color_classifier.py. Where the geometry track has its own
CNN (classifier.py) backing up clubbing/koilonychia geometry, this backs up the
classical colour heuristics (cyanosis.py, terrys_nails.py, beaus_lines.py,
muehrckes_lines.py, pitting.py) -- most of which calibrated near chance on real photos
(ml/eval/calibrate_color.py). A CNN trained on the same KNM labels does better, and
color_fusion.py combines the two per condition.

Same lazy + optional contract as classifier.py: torch and the weights load on first
use, and is_available() lets pipeline.analyze_top_color skip the CNN entirely (the
classical findings still ship) when torch isn't installed or no colour model is
trained. Manifest + weights are SEPARATE from the geometry CNN's
(nail_color_classifier_labels.json / nail_color_classifier__<backbone>.pt).

Crop parity: the model trained on nail-plate box crops, so at inference we classify a
crop of nail_region's detected nail bbox (predict_from_region) -- the closest
inference-time analogue to the training crop. The model has more classes than the app
reports (it also learned melanoma / onychogryphosis / clubbing / koilonychia, purely
to discriminate); color_fusion only consults the prediction for the five app colour
conditions.

HONESTY: trained on clinical photos, not phone photos -- real-world accuracy unknown
and never clinical-grade. Output stays within / outside / inconclusive, never a
diagnosis.
"""

import json
from pathlib import Path

import cv2

_MODELS = Path(__file__).resolve().parent.parent / "models"
_LABELS_PATH = _MODELS / "nail_color_classifier_labels.json"

# 11-class model -> chance is ~0.09; this is a deliberately cautious, calibrated floor.
# Below it we treat the CNN as having no opinion (color_fusion falls back to classical).
CONFIDENCE_THRESHOLD = 0.45

# Per-class override of the floor above. `pallor` (added when the Ghana
# fingernail-anemia set was folded in -- see scripts/build_color_classification_dataset.py)
# sits at precision 0.688 at the global 0.45 floor on the held-out test set, because
# anemic-vs-non-anemic nail colour is a genuinely subtle visual call -- the errors
# concentrate entirely within that cohort's images, not elsewhere. Measured on the same
# test set, confidence is a real precision signal for this class (0.45->0.688P/0.883R,
# 0.65->0.792P/0.678R), so a class-specific floor of 0.65 trades some recall for a false
# "outside" rate low enough to show a user. Re-measure if the dataset changes.
CLASS_CONFIDENCE_THRESHOLD = {"pallor": 0.65}

# Must match scripts/build_color_classification_dataset.py's BOX_PAD_FRAC so the
# inference crop matches the training crop framing.
BOX_PAD_FRAC = 0.15

_state = {"loaded": False}


def _members_from_meta(meta):
    return [(m["backbone"], m["weights_file"], float(m.get("temperature", 1.0)))
            for m in meta.get("ensemble", [])]


def is_available():
    """True iff the manifest + >=1 member's weights exist and torch imports."""
    if not _LABELS_PATH.exists():
        return False
    try:
        meta = json.loads(_LABELS_PATH.read_text())
    except (OSError, ValueError):
        return False
    if not any((_MODELS / wf).exists() for _, wf, _ in _members_from_meta(meta)):
        return False
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except ImportError:
        return False
    return True


def app_conditions():
    """The colour conditions the trained model can speak to (subset of its classes)."""
    try:
        meta = json.loads(_LABELS_PATH.read_text())
    except (OSError, ValueError):
        return []
    return list(meta.get("app_conditions", []))


def _build_backbone(name, num_classes):
    from torch import nn
    from torchvision import models

    if name == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None); head = 3
    elif name == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None); head = 1
    else:
        raise ValueError(f"unknown backbone {name}")
    in_features = model.classifier[head].in_features
    model.classifier[head] = nn.Linear(in_features, num_classes)
    return model


def _load():
    if _state["loaded"]:
        return _state
    import torch
    from torchvision import transforms

    meta = json.loads(_LABELS_PATH.read_text())
    members = []
    for backbone, weights_file, temperature in _members_from_meta(meta):
        wpath = _MODELS / weights_file
        if not wpath.exists():
            continue
        model = _build_backbone(backbone, len(meta["classes"]))
        model.load_state_dict(torch.load(wpath, map_location="cpu"))
        model.eval()
        members.append((model, temperature))

    tf = transforms.Compose([
        transforms.Resize(256, antialias=True),
        transforms.CenterCrop(meta["img_size"]),
        transforms.Normalize(meta["mean"], meta["std"]),
    ])
    _state.update(loaded=True, members=members, meta=meta, tf=tf, torch=torch)
    return _state


def classify_nail_bgr(nail_bgr):
    """Return (top_label, top_prob, {label: prob}) for a nail-plate crop.

    Ensembled, temperature-scaled, TTA'd (image + horizontal flip), exactly like the
    geometry CNN so calibration carries over.
    """
    s = _load()
    torch = s["torch"]

    rgb = cv2.cvtColor(nail_bgr, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    base = s["tf"](tensor)
    views = torch.stack([base, torch.flip(base, dims=[2])])

    probs_sum = None
    with torch.no_grad():
        for model, temperature in s["members"]:
            p = torch.softmax(model(views) / temperature, dim=1).mean(dim=0)
            probs_sum = p if probs_sum is None else probs_sum + p
    probs = probs_sum / len(s["members"])

    classes = s["meta"]["classes"]
    idx = int(probs.argmax())
    all_probs = {c: round(float(probs[i]), 3) for i, c in enumerate(classes)}
    return classes[idx], float(probs[idx]), all_probs


def _crop_to_bbox(image_bgr, bbox_norm):
    """Crop image to nail_region's normalized bbox, padded to match training framing."""
    h, w = image_bgr.shape[:2]
    x0, y0, x1, y1 = bbox_norm
    bw, bh = (x1 - x0) * w, (y1 - y0) * h
    px, py = bw * BOX_PAD_FRAC, bh * BOX_PAD_FRAC
    a = max(0, int(x0 * w - px)); b = min(w, int(x1 * w + px))
    c = max(0, int(y0 * h - py)); d = min(h, int(y1 * h + py))
    if b - a < 8 or d - c < 8:
        return image_bgr
    return image_bgr[c:d, a:b]


def predict_from_region(image_bgr, region):
    """CNN opinion for color_fusion, or None if the CNN has no confident call.

    Returns {"predicted_label", "confidence", "probs"} where predicted_label is the
    top class (or None when below CONFIDENCE_THRESHOLD -- treated as no opinion).
    Crops to the nail bbox first so the model sees what it trained on.
    """
    bbox = region.get("bbox_norm")
    nail = _crop_to_bbox(image_bgr, bbox) if bbox is not None else image_bgr
    if nail is None or nail.size == 0:
        return None
    label, prob, all_probs = classify_nail_bgr(nail)
    threshold = CLASS_CONFIDENCE_THRESHOLD.get(label, CONFIDENCE_THRESHOLD)
    if prob < threshold:
        return {"predicted_label": None, "confidence": round(prob, 3), "probs": all_probs}
    return {"predicted_label": label, "confidence": round(prob, 3), "probs": all_probs}
