"""Trained-CNN track: a MobileNetV3 classifying nail condition from a photo.

Companion to ml/train/train_classifier.py, which produces the weights this loads
(ml/models/nail_classifier.pt + nail_classifier_labels.json).

This is the second analysis track alongside the geometry in clubbing.py /
koilonychia.py. Everything here is lazy + optional: torch and the weights file
are only touched on first use, and is_available() lets the pipeline skip the ML
findings entirely (geometry still works) if torch isn't installed or the model
hasn't been trained yet. That keeps the Flask app runnable in a torch-free env.

Three things make the prediction trustworthy rather than a raw softmax guess:
  - ROI crop: the finger is cropped out of the frame first (crop_to_finger_roi)
    so the CNN classifies the nail, not the background it happens to sit on.
  - TTA: the prediction is averaged over a few flips/crops for a steadier read.
  - Temperature scaling: logits are divided by a calibration temperature fit on
    the validation set, so the probability the CONFIDENCE_THRESHOLD gates on is
    closer to a real probability instead of an over-confident softmax.

HONESTY: the model was trained on mostly top-down/frontal nail images. A side
profile is a different view, so side-view ML output is a weaker signal than the
top-down one -- the geometry track is the authority on the side profile.
"""

import json
from pathlib import Path

import cv2

from .preprocessing import crop_to_finger_roi

_MODELS = Path(__file__).resolve().parent.parent / "models"
_MODEL_PATH = _MODELS / "nail_classifier.pt"
_LABELS_PATH = _MODELS / "nail_classifier_labels.json"

# Below this top-class probability we say "couldn't analyze" rather than guess
# (3 classes -> 0.33 is chance; 0.50 is a deliberately cautious floor). Because
# logits are temperature-calibrated, this floor is meaningful, not a raw-softmax
# number that's confidently wrong on out-of-distribution photos.
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


def _build_backbone(name, num_classes):
    """Recreate the architecture the weights were trained with (no pretrained DL)."""
    from torch import nn
    from torchvision import models

    if name == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
    else:  # mobilenet_v3_small -- the original/back-compat default
        model = models.mobilenet_v3_small(weights=None)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, num_classes)
    return model


def _load():
    if _state["loaded"]:
        return _state
    import torch
    from torchvision import transforms

    meta = json.loads(_LABELS_PATH.read_text(encoding="utf-8"))
    model = _build_backbone(meta.get("backbone", "mobilenet_v3_small"), len(meta["classes"]))
    model.load_state_dict(torch.load(_MODEL_PATH, map_location="cpu"))
    model.eval()

    tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(meta["img_size"]),
        transforms.Normalize(meta["mean"], meta["std"]),
    ])
    _state.update(
        loaded=True, model=model, meta=meta, tf=tf, torch=torch,
        temperature=float(meta.get("temperature", 1.0)),
    )
    return _state


def _logits(model, x, torch):
    with torch.no_grad():
        return model(x)


def classify_bgr(image_bgr):
    """Return (top_label, top_prob, {label: prob}) for a decoded BGR image.

    Crops to the finger ROI, runs test-time augmentation (original + horizontal
    flip), averages the temperature-scaled probabilities, and returns the top.
    """
    s = _load()
    torch = s["torch"]
    temperature = s["temperature"]

    roi = crop_to_finger_roi(image_bgr)
    rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    base = s["tf"](tensor)

    # TTA: average probabilities over the image and its horizontal flip. Cheap,
    # and steadies the confidence enough to matter for the threshold gate.
    views = torch.stack([base, torch.flip(base, dims=[2])])
    logits = _logits(s["model"], views, torch) / temperature
    probs = torch.softmax(logits, dim=1).mean(dim=0)

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
