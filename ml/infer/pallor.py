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

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# Pallor screening from nail color needs a labeled dataset to validate, which
# doesn't exist yet.
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
