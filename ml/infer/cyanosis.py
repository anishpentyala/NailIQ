"""Cyanosis (bluish nail discoloration) -- color track, top-down photo.

Classical CV like the color conditions: from the nail region (nail_region.py) we
measure how blue the nail plate is on the CIELab b* axis (lower b* = bluer). A
distinctly blue nail can reflect low blood oxygen. No trained model needed.

Important design note: cyanosis reads `nail_raw_lab_b` -- the b* of the nail measured
*before* white-balancing -- not the white-balanced `lab_b` the other color conditions
use. Central cyanosis is a global bluish cast, and the Shades-of-Gray white balance in
nail_region is built to remove global casts, so it erases the very sign. An earlier
version compared white-balanced nail b* to skin b* and, on 88 real labeled "blue nail"
photos vs 80 healthy, separated them no better than a coin flip (balanced accuracy ~0.53)
-- because both the cast removal and the nail-vs-skin comparison cancel a whole-finger
blue tint. Reading the raw (pre-WB) blueness instead lifts that to ~0.67.

Still a heuristic screener hint on a noisy, heterogeneous dataset -- never an oxygenation
test or diagnosis.
"""

import numpy as np

from .nail_region import heuristic_confidence

# Calibrated 2026-06-24 against the KNM nail-disease dataset (Roboflow, CC BY 4.0):
# 88 labeled blue-nail photos vs 80 healthy, full-image (margin-padded) through this
# pipeline -- see ml/eval/calibrate_color.py + scripts/build_color_eval_set.py. A nail
# whose RAW (pre-white-balance) b* is below this reads as bluish. At 5.0 the sweep's
# best operating point gives sensitivity 0.40 at specificity 0.95 (balanced acc 0.67),
# beating the old white-balanced relative-to-skin metric on both axes (it sat at ~chance).
# Clinical-photo dataset, not real phone photos -- real-world accuracy still unknown.
CYANOSIS_RAW_B_MAX = 5.0


def measure(region):
    """Return the nail's raw (pre-white-balance) b* (lower = bluer).

    Falls back to the white-balanced nail b* median only if an older region dict
    lacks nail_raw_lab_b, so callers never crash on a stale region.
    """
    raw_b = region.get("nail_raw_lab_b")
    if raw_b is None:
        raw_b = float(np.median(region["lab_b"]))
    return float(raw_b)


def to_verdict(raw_b):
    """outside if the nail is distinctly blue (raw b* below the calibrated cutoff)."""
    return "outside" if raw_b < CYANOSIS_RAW_B_MAX else "within"


def build_finding(region):
    raw_b = measure(region)
    return {
        "label": "cyanosis",
        "display_name": "Nail color (cyanosis)",
        "value": None,
        "unit": None,
        "verdict": to_verdict(raw_b),
        "confidence": heuristic_confidence(raw_b, CYANOSIS_RAW_B_MAX),
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
