"""Trained-CNN track: MobileNetV3-Small classifying nail condition from a photo.

Companion to ml/train/train_classifier.py, which produces the weights this loads
(ml/models/nail_classifier.pt + nail_classifier_labels.json).

This is the second analysis track alongside the geometry in clubbing.py /
koilonychia.py. Everything here is lazy + optional: torch and the weights file
are only touched on first use, and is_available() lets the pipeline skip the ML
findings entirely (geometry still works) if torch isn't installed or the model
hasn't been trained yet. That keeps the Flask app runnable in a torch-free env.

HONESTY: the model was trained on mostly top-down/frontal nail images. A side
profile is a different view, so side-view ML output is a weaker signal than the
top-down one -- the geometry track is the authority on the side profile.
"""

import json
from pathlib import Path

import cv2

_MODELS = Path(__file__).resolve().parent.parent / "models"
_MODEL_PATH = _MODELS / "nail_classifier.pt"
_LABELS_PATH = _MODELS / "nail_classifier_labels.json"

# Below this top-class probability we say "couldn't analyze" rather than guess
# (3 classes -> 0.33 is chance; 0.50 is a deliberately cautious floor).
CONFIDENCE_THRESHOLD = 0.50

# Predicted classes that mean "a sign is present" -> outside typical range.
# "healthy" -> within. Anything else added later defaults to outside.
WITHIN_LABELS = {"healthy"}

_state = {"loaded": False}


def is_available():
    """True iff the model file exists and torch/torchvision can be imported."""
    if not (_MODEL_PATH.exists() and _LABELS_PATH.exists()):
        return False
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except ImportError:
        return False
    return True


def _load():
    if _state["loaded"]:
        return _state
    import torch
    from torch import nn
    from torchvision import models, transforms

    meta = json.loads(_LABELS_PATH.read_text(encoding="utf-8"))
    model = models.mobilenet_v3_small(weights=None)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, len(meta["classes"]))
    model.load_state_dict(torch.load(_MODEL_PATH, map_location="cpu"))
    model.eval()

    tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(meta["img_size"]),
        transforms.Normalize(meta["mean"], meta["std"]),
    ])
    _state.update(loaded=True, model=model, meta=meta, tf=tf, torch=torch)
    return _state


def classify_bgr(image_bgr):
    """Return (top_label, top_prob, {label: prob}) for a decoded BGR image."""
    s = _load()
    torch = s["torch"]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    x = s["tf"](tensor).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(s["model"](x), dim=1)[0]
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
