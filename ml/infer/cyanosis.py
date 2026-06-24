"""Cyanosis (bluish nail discoloration) -- color track, top-down photo.

Classical CV like the color conditions: from the nail region (nail_region.py)
we measure the CIELab b* coordinate (blue-yellow axis) of the nail pixels.
A nail significantly bluer than the person's own skin may indicate low blood oxygen.
No trained model needed.

Note: this is a heuristic detector. A truly bluish nail (negative b*) is flagged if it
is notably bluer than the person's skin. This is an uncalibrated color signal and should
never be presented as an oxygenation test or clinical diagnostic — it's a screener hint only.
"""

import numpy as np

from .nail_region import heuristic_confidence

# Rough starting estimate -- uncalibrated; no labeled dataset yet.
# A nail b* below this value reads as bluish (not yellow/normal).
CYANOSIS_B_MAX = 5.0

# Rough starting estimate -- uncalibrated; no labeled dataset yet.
# The nail must be at least this many units bluer (lower b*) than the person's
# own skin b* to flag cyanosis.
CYANOSIS_BLUER_THAN_SKIN = 6.0


def measure(region):
    """Measure nail b* (Lab blue-yellow) and the difference from skin.

    Returns (nail_b, bluer_than_skin).
    """
    nail_b = float(np.median(region["lab_b"]))
    skin_b = region["skin_lab_b"]

    # If skin reference is available, use it; otherwise compare to an implicit zero (white).
    bluer_than_skin = (skin_b - nail_b) if skin_b is not None else (0.0 - nail_b)

    return nail_b, bluer_than_skin


def to_verdict(nail_b, bluer_than_skin):
    """Determine verdict: outside if nail is both very blue AND bluer than skin,
    else within."""
    if nail_b < CYANOSIS_B_MAX and bluer_than_skin > CYANOSIS_BLUER_THAN_SKIN:
        return "outside"
    return "within"


def build_finding(region):
    nail_b, bluer_than_skin = measure(region)
    return {
        "label": "cyanosis",
        "display_name": "Nail color (cyanosis)",
        "value": None,
        "unit": None,
        "verdict": to_verdict(nail_b, bluer_than_skin),
        "confidence": heuristic_confidence(bluer_than_skin, CYANOSIS_BLUER_THAN_SKIN),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "cyanosis",
        "display_name": "Nail color (cyanosis)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
