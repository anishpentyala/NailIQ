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
to discriminate); color_fusion only consults the prediction for the app colour
conditions it covers (cyanosis, terrys_nails, beaus_lines, muehrckes_lines, pitting,
pallor, leukonychia, onycholysis, splinter_hemorrhages, lindsays_nails, and --
once the arthitaya set was folded in -- melanonychia, the last previously
heuristic-only condition).

HONESTY: trained on clinical photos, not phone photos -- real-world accuracy unknown
and never clinical-grade. Output stays within / outside / inconclusive, never a
diagnosis.
"""

import json
from pathlib import Path

import cv2

_MODELS = Path(__file__).resolve().parent.parent / "models"
_LABELS_PATH = _MODELS / "nail_color_classifier_labels.json"

# This default floor is independently overridden by frozen candidate decision rules.
# Below it we treat the CNN as having no opinion (color_fusion falls back to classical).
CONFIDENCE_THRESHOLD = 0.45

# Per-class override of the floor above. Each cutoff below is chosen by
# ml/eval/sweep_color_thresholds.py on the VALID split, then its precision/recall is
# measured once, on TEST, at that fixed cutoff -- the sweep and the report use
# different data on purpose. An earlier version of this file swept AND reported on
# the same test split (classic cutoff-selection leakage: the "P/R at this cutoff"
# numbers were optimistic by construction). Re-run that script and update the numbers
# below after any retrain -- they will also shift because the model changes, not only
# because of which split picked the cutoff.
CLASS_CONFIDENCE_THRESHOLD = {
    # pallor: the valid-picked cutoff was 0.70 (test P 0.878/R 0.565), but end-to-end
    # sensitivity (ml/eval/eval_color_sensitivity.py) showed that cost real recall for
    # no measured benefit: at 0.70, real anemic photos were caught only ~20-28% of the
    # time. Overriding down to 0.45 (test P 0.741/R 0.835) nearly quadrupled end-to-end
    # recall to 76.2% while the healthy-image false-positive rate stayed exactly the
    # same (0.9%) -- the confidence range this floor change opens up (0.45-0.70) turned
    # out to hold real anemic cases, not borderline healthy ones. Re-verify both numbers
    # (not just the isolated CNN test) if this ever gets re-swept. NOTE: the isolated
    # P/R figures above predate the 2026-09 nail-disease-removal retrain (below); only
    # ml/eval/tune_color_decision.py's end-to-end recall/FP were re-verified against the
    # new model, and confirmed 0.45 is still valid-optimal for this condition.
    "pallor": 0.45,
    # splinter_hemorrhages: chosen by ml/eval/tune_color_decision.py on VALID after the
    # chaa dataset (scripts/build_color_classification_dataset.py) replaced nail-disease
    # as this condition's CNN training source in 2026-09 -- see that script's module
    # docstring. End-to-end (through /analyze), VALID: recall 73.2%->75.6%, FP
    # 4.6%->2.1% at this floor (n_pos=41). This is the first cutoff for this condition
    # chosen against real, uncontaminated positives (previously nail-disease supplied
    # both the training data AND the eval positives, so its watermark-contamination risk
    # was invisible to every past number here).
    "splinter_hemorrhages": 0.40,
    # terrys_nails: chosen by ml/eval/tune_color_decision.py after the 2026-09-16
    # NIHATI/anemia retrain -- lowering the top-class floor from the 0.45 default to
    # 0.25 raised end-to-end valid recall 44.1%->50.0% at FP 1.7%->2.6%.
    "terrys_nails": 0.25,
    # Melanonychia remains absent from the production manifest. User-authorized
    # Arthitaya candidates can cover it; their tiny validation pool does not by
    # itself justify changing the production evidence gate.
    #
    # leukonychia/onycholysis/lindsays_nails lost their CNN class entirely in 2026-09
    # when nail-disease (their only training source) was removed for watermark
    # contamination. As of 2026-09-16 the NIHATI dataset (a separately vetted,
    # algorithmically-audited Roboflow source, see scripts/build_color_classification_
    # dataset.py's add_nihati) restored all three as model classes -- none of the three
    # needed a floor override here (VALID-picked floor for all three was "keep the 0.45
    # default"; only their OVR/support tables changed, see color_fusion.py). Their eval
    # positive counts from NIHATI are still tiny (n=4-6 on VALID) -- see
    # ml/infer/validation_policy.py and color_fusion.LOW_SAMPLE_CONDITIONS for how that
    # caveat is handled.
}

# Must match scripts/build_color_classification_dataset.py's BOX_PAD_FRAC so the
# inference crop matches the training crop framing.
BOX_PAD_FRAC = 0.15
_DEFAULT_CLASS_THRESHOLDS = dict(CLASS_CONFIDENCE_THRESHOLD)

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


def model_metadata():
    if not _LABELS_PATH.is_file():
        return {}
    try:
        metadata = json.loads(_LABELS_PATH.read_text())
        return metadata if isinstance(metadata, dict) else {}
    except (OSError, ValueError):
        return {}


def configure_manifest_rules():
    from . import color_fusion
    for condition, rule in model_metadata().get('decision_rules', {}).items():
        floor, ovr, support = rule
        for table, value in ((CLASS_CONFIDENCE_THRESHOLD, floor),
                             (color_fusion.OVR_THRESHOLD, ovr),
                             (color_fusion.HEURISTIC_MIN_CNN_SUPPORT, support)):
            if value is None:
                table.pop(condition, None)
            else:
                table[condition] = value
    for condition, rule in model_metadata().get('appearance_rules', {}).items():
        CLASS_CONFIDENCE_THRESHOLD[condition] = rule.get('floor', 0.5)


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

    configure_manifest_rules()

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
    # Only models trained on tip-down crops (manifest flag) get rotated input.
    if region.get("tip_vec") is not None and model_metadata().get("canonical_orientation"):
        from . import orientation
        nail = orientation.rotate_tip_down(nail, orientation.direction_from_vector(*region["tip_vec"]))
    _, _, all_probs = classify_nail_bgr(nail)
    return opinion_from_probs(all_probs)


def opinion_from_probs(all_probs, thresholds=None):
    """Top class if it clears its confidence floor, else no opinion. Split out so
    ml/eval/tune_color_decision.py replays exactly this rule from cached probs."""
    if not all_probs:
        return None
    label = max(all_probs, key=all_probs.get)
    prob = all_probs[label]
    threshold = (CLASS_CONFIDENCE_THRESHOLD if thresholds is None else thresholds).get(label, CONFIDENCE_THRESHOLD)
    return {"predicted_label": label if prob >= threshold else None,
            "confidence": round(prob, 3), "probs": all_probs}
