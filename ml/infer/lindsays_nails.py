"""Lindsay's nails (half-and-half nails: proximal ~50% white/opaque, distal ~50% darker reddish-brown) -- color track, top-down photo.

Classical CV like the geometry conditions: from the nail region (nail_region.py)
we measure the whiteness of the proximal nail and the brightness contrast between
proximal and distal sections, flagging a strong white proximal half with a notably
darker distal half as outside typical range. No trained model needed.

Differs from Terry's nails (terrys_nails.py) in the split: Terry's is ~80% proximal
white with a narrow distal band; Lindsay's is approximately 50/50.
"""

import numpy as np
import warnings
from .nail_region import heuristic_confidence, GRID_H, GRID_W

# A cell counts as "white" in the proximal region: high value, low saturation.
LINDSAY_V_MIN = 0.78
LINDSAY_S_MAX = 0.25

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# Distinguishes Lindsay's nails (strong proximal-distal contrast over ~50% split)
# from normal nails.
LINDSAY_CONTRAST_THRESHOLD = 0.12

# Proximal region must be sufficiently white before the contrast is evaluated.
LINDSAY_WHITE_FRAC_GATE = 0.5


def measure(region):
    """Return (prox_white_frac, contrast).

    prox_white_frac: fraction of non-NaN proximal cells where V > LINDSAY_V_MIN and S < LINDSAY_S_MAX.
    contrast: nanmean(proximal V) - nanmean(distal V).
    """
    grid_v = region["grid_v"]
    grid_s = region["grid_s"]

    # Split into proximal (0 to 50% of nail length) and distal (50% to 100%).
    mid = GRID_H // 2
    grid_v_prox = grid_v[:mid]
    grid_s_prox = grid_s[:mid]
    grid_v_distal = grid_v[mid:]
    grid_s_distal = grid_s[mid:]

    # Proximal white fraction: count cells where V > threshold and S < threshold.
    white_cells = (grid_v_prox > LINDSAY_V_MIN) & (grid_s_prox < LINDSAY_S_MAX)
    non_nan_cells = ~np.isnan(grid_v_prox)
    if non_nan_cells.sum() == 0:
        prox_white_frac = 0.0
    else:
        prox_white_frac = float(white_cells.sum() / non_nan_cells.sum())

    # Brightness contrast: proximal brighter than distal.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        prox_v_mean = np.nanmean(grid_v_prox)
        distal_v_mean = np.nanmean(grid_v_distal)

    if np.isnan(prox_v_mean) or np.isnan(distal_v_mean):
        contrast = 0.0
    else:
        contrast = prox_v_mean - distal_v_mean

    return prox_white_frac, contrast


def to_verdict(prox_white_frac, contrast):
    """Return "outside" if both whiteness and contrast thresholds are met, else "within"."""
    if prox_white_frac > LINDSAY_WHITE_FRAC_GATE and contrast > LINDSAY_CONTRAST_THRESHOLD:
        return "outside"
    return "within"


def build_finding(region):
    prox_white_frac, contrast = measure(region)
    return {
        "label": "lindsays_nails",
        "display_name": "Nail color (half-and-half nails)",
        "value": None,
        "unit": None,
        "verdict": to_verdict(prox_white_frac, contrast),
        "confidence": heuristic_confidence(contrast, LINDSAY_CONTRAST_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "lindsays_nails",
        "display_name": "Nail color (half-and-half nails)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
