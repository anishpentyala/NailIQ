"""Pallor (abnormally pale nail bed) -- color track, top-down photo.

Classical CV like leukonychia: from the nail region (nail_region.py) we measure
the redness of the nail pixels relative to the person's own skin, and flag an
abnormally pale nail (much less red than skin, and low in absolute redness) as
outside typical range. No trained model needed.

This is a precautionary screener only. Pallor can be a sign of anemia or poor
perfusion, but the heuristic here is uncalibrated and needs validation against
a labeled dataset. Never present it as a clinical-grade anemia test.
"""

import numpy as np

from .nail_region import heuristic_confidence

# A pale nail is much LESS red than the person's own skin AND has low absolute
# redness. The skin-relative threshold catches "pale-for-this-person"; the
# absolute threshold separates pallor from simply darker skin tones.

# Rough starting estimate, still UNCALIBRATED. A calibration attempt on 2026-06-24
# against the Ghana fingernail-anemia dataset (Mendeley, CC BY 4.0; 314 anemic vs 221
# non-anemic, one original per patient -- see scripts/build_color_eval_set.py) did NOT
# yield a usable threshold: best achievable balanced accuracy was ~0.57 (≈ chance). Two
# reasons, both honest limitations rather than a tuning miss: (1) that dataset is nail-ONLY
# crops with no surrounding skin, so this skin-relative metric can't actually be exercised
# on it (and absolute nail color separated the classes no better); (2) nail-bed pallor from
# anemia is a subtle, skin-tone-confounded sign that simple color statistics don't capture
# -- the published work on that dataset uses CNNs and still reports only ~70-77%. So pallor
# stays on these estimates and leans toward within/inconclusive. Real calibration needs
# finger-with-skin photos labeled for visible pallor, which we don't have.
PALLOR_REDNESS_DROP_THRESHOLD = 8.0
PALLOR_ABS_A_MAX = 12.0


def measure(region):
    """Return (nail_a, redness_drop). If skin_lab_a is None, raises ValueError."""
    if region["skin_lab_a"] is None:
        raise ValueError("skin_lab_a is None")
    nail_a = float(np.median(region["lab_a"]))
    redness_drop = region["skin_lab_a"] - nail_a
    return nail_a, redness_drop


def to_verdict(nail_a, redness_drop):
    """Return "outside" if pallor is detected, else "within"."""
    if redness_drop > PALLOR_REDNESS_DROP_THRESHOLD and nail_a < PALLOR_ABS_A_MAX:
        return "outside"
    return "within"


def build_finding(region):
    """Build a pallor finding from the nail region dict."""
    if region["skin_lab_a"] is None:
        return inconclusive_finding("nail_region_unclear")
    try:
        nail_a, redness_drop = measure(region)
    except (ValueError, TypeError):
        return inconclusive_finding("nail_region_unclear")
    verdict = to_verdict(nail_a, redness_drop)
    confidence = heuristic_confidence(redness_drop, PALLOR_REDNESS_DROP_THRESHOLD)
    return {
        "label": "pallor",
        "display_name": "Nail color (pallor)",
        "value": None,
        "unit": None,
        "verdict": verdict,
        "confidence": confidence,
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    """Return an inconclusive pallor finding."""
    return {
        "label": "pallor",
        "display_name": "Nail color (pallor)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
