"""Terry's nails (proximal nail plate opaque white, narrow darker distal band) -- color track, top-down photo.

Classical CV like the geometry conditions: from the nail region (nail_region.py)
we measure the whiteness of the proximal nail and the brightness contrast between
proximal and distal sections, flagging a strong white proximal with darker distal
band as outside typical range. No trained model needed.
"""

import numpy as np
from .nail_region import heuristic_confidence, GRID_H, GRID_W

# A cell counts as "white" in the proximal region: high value, low saturation.
TERRYS_V_MIN = 0.78
TERRYS_S_MAX = 0.22

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# Distinguishes Terry's (strong proximal-distal contrast) from normal nails.
TERRYS_CONTRAST_THRESHOLD = 0.12

# Proximal region must be sufficiently white before the contrast is evaluated.
TERRYS_WHITE_FRAC_GATE = 0.5


def measure(region):
    """Return (prox_white_frac, band_contrast).

    prox_white_frac: fraction of non-NaN proximal cells where V > TERRYS_V_MIN and S < TERRYS_S_MAX.
    band_contrast: nanmean(proximal V) - nanmean(distal V).
    """
    grid_v = region["grid_v"]
    grid_s = region["grid_s"]

    # Split into proximal (0 to 80% of nail length) and distal (80% to 100%).
    prox_idx = int(0.8 * GRID_H)
    grid_v_prox = grid_v[:prox_idx]
    grid_s_prox = grid_s[:prox_idx]
    grid_v_distal = grid_v[prox_idx:]
    grid_s_distal = grid_s[prox_idx:]

    # Proximal white fraction: count cells where V > threshold and S < threshold.
    white_cells = (grid_v_prox > TERRYS_V_MIN) & (grid_s_prox < TERRYS_S_MAX)
    non_nan_cells = ~np.isnan(grid_v_prox)
    if non_nan_cells.sum() == 0:
        prox_white_frac = 0.0
    else:
        prox_white_frac = float(white_cells.sum() / non_nan_cells.sum())

    # Brightness contrast: proximal darker than distal (inverted vs leukonychia).
    prox_v_mean = np.nanmean(grid_v_prox)
    distal_v_mean = np.nanmean(grid_v_distal)
    band_contrast = prox_v_mean - distal_v_mean

    return prox_white_frac, band_contrast


def to_verdict(prox_white_frac, band_contrast):
    """Return "outside" if both whiteness and contrast thresholds are met, else "within"."""
    if prox_white_frac > TERRYS_WHITE_FRAC_GATE and band_contrast > TERRYS_CONTRAST_THRESHOLD:
        return "outside"
    return "within"


def build_finding(region):
    prox_white_frac, band_contrast = measure(region)
    return {
        "label": "terrys_nails",
        "display_name": "Nail color (Terry's nails)",
        "value": None,
        "unit": None,
        "verdict": to_verdict(prox_white_frac, band_contrast),
        "confidence": heuristic_confidence(band_contrast, TERRYS_CONTRAST_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "terrys_nails",
        "display_name": "Nail color (Terry's nails)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
