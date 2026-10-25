"""Trained-CNN track: an ensemble of MobileNetV3 / EfficientNet classifying nail
condition from a photo.

Companion to ml/train/train_classifier.py, which trains each backbone and registers
it in the manifest this loads (ml/models/nail_classifier_labels.json + one
nail_classifier__<backbone>.pt per member).

This is the second analysis track alongside the geometry in clubbing.py /
koilonychia.py. Everything here is lazy + optional: torch and the weights are only
touched on first use, and is_available() lets the pipeline skip the ML findings
entirely (geometry still works) if torch isn't installed or no model is trained.
That keeps the Flask app runnable in a torch-free env.

Four things make the prediction trustworthy rather than a raw softmax guess:
  - ROI crop: the finger is cropped out of the frame first (crop_to_finger_roi)
    so the CNN classifies the nail, not the background it sits on.
  - Ensemble: probabilities are averaged across diverse backbones (a wrong call by
    one is usually outvoted), which beats any single model.
  - TTA: each model is also averaged over the image + its horizontal flip.
  - Temperature scaling: each member's logits are divided by a temperature fit on
    the validation set, so the probability CONFIDENCE_THRESHOLD gates on is
    calibrated, not over-confident.

HONESTY: the models trained on mostly top-down/frontal nail images. A side profile
is a different view, so side-view ML output is weaker than the top-down one -- the
geometry track is the authority on the side profile.
"""

import json
from pathlib import Path

import cv2

from . import onnx_backend
from .preprocessing import crop_to_finger_roi

_MODELS = Path(__file__).resolve().parent.parent / "models"
_LABELS_PATH = _MODELS / "nail_classifier_labels.json"
_LEGACY_WEIGHTS = _MODELS / "nail_classifier.pt"  # pre-ensemble single-file format

# Below this top-class probability we say "couldn't analyze" rather than guess
# (3 classes -> 0.33 is chance; 0.50 is a deliberately cautious, calibrated floor).
CONFIDENCE_THRESHOLD = 0.50

# Predicted classes meaning "a sign is present" -> outside typical range.
WITHIN_LABELS = {"healthy"}

_state = {"loaded": False}


def _members_from_meta(meta):
    """Normalize old + new manifest formats to a list of (backbone, weights_file, temp)."""
    if meta.get("ensemble"):
        return [(m["backbone"], m["weights_file"], float(m.get("temperature", 1.0)))
                for m in meta["ensemble"]]
    # Legacy single-file format.
    return [(meta.get("backbone", "mobilenet_v3_small"), _LEGACY_WEIGHTS.name,
             float(meta.get("temperature", 1.0)))]


def is_available():
    """True iff the manifest + at least one member's weights exist and torch imports."""
    if not _LABELS_PATH.exists():
        return False
    try:
        meta = json.loads(_LABELS_PATH.read_text())
    except (OSError, ValueError):
        return False
    if onnx_backend.active():
        return any(onnx_backend.has(onnx_backend.onnx_name(wf)) for _, wf, _ in _members_from_meta(meta))
    if not any((_MODELS / wf).exists() for _, wf, _ in _members_from_meta(meta)):
        return False
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except ImportError:
        return False
    return True


def _build_backbone(name, num_classes):
    """Recreate an architecture matching trained weights (no pretrained download)."""
    from torch import nn
    from torchvision import models

    if name == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None); head = 3
    elif name == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None); head = 1
    else:  # mobilenet_v3_small -- legacy default
        model = models.mobilenet_v3_small(weights=None); head = 3
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


def classify_bgr(image_bgr):
    """Return (top_label, top_prob, {label: prob}) for a decoded BGR image.

    Crops to the finger ROI, then averages temperature-scaled, TTA'd probabilities
    across every ensemble member.
    """
    roi = crop_to_finger_roi(image_bgr)
    rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    if onnx_backend.active():
        meta = json.loads(_LABELS_PATH.read_text())
        members = [(wf, t) for _, wf, t in _members_from_meta(meta) if onnx_backend.has(onnx_backend.onnx_name(wf))]
        probs = onnx_backend.ensemble_probs(meta, members, rgb)
        classes = meta["classes"]
        idx = int(probs.argmax())
        return classes[idx], float(probs[idx]), {c: round(float(probs[i]), 3) for i, c in enumerate(classes)}

    s = _load()
    torch = s["torch"]
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    base = s["tf"](tensor)
    views = torch.stack([base, torch.flip(base, dims=[2])])  # TTA: image + h-flip

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


def build_finding(image_bgr, view):
    """One ML finding for a single photo. `view` is 'side' or 'top'."""
    display = f"AI nail check ({view} view)"
    label, prob, all_probs = classify_bgr(image_bgr)

    if prob < CONFIDENCE_THRESHOLD:
        return {
            "label": f"ml_{view}",
            "display_name": display,
            "value": None,
            "unit": None,
            "verdict": "inconclusive",
            "confidence": round(prob, 3),
            "predicted_label": None,
            "probs": all_probs,
            "track_used": "ml",
            "failure_reason": "low_confidence",
        }

    verdict = "within" if label in WITHIN_LABELS else "outside"
    return {
        "label": f"ml_{view}",
        "display_name": display,
        "value": None,
        "unit": None,
        "verdict": verdict,
        "confidence": round(prob, 3),
        "predicted_label": label,
        "probs": all_probs,
        "track_used": "ml",
        "failure_reason": None,
    }
