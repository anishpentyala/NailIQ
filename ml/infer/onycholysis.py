"""Onycholysis (nail separation from the bed, distal zone appears opaque/white) -- color track, top-down photo.

Classical CV: from the nail region (nail_region.py) we measure the whiteness of the
distal third of the nail and compare it to the proximal two-thirds. A distal zone
that is specifically whiter than the rest distinguishes onycholysis (separation at
the free edge) from generalized leukonychia (whitening everywhere). No trained model needed.
"""

import numpy as np
from .nail_region import heuristic_confidence, GRID_H, GRID_W

# A cell counts as "white" in the distal region: high value, low saturation.
ONYCHOLYSIS_V_MIN = 0.78
ONYCHOLYSIS_S_MAX = 0.25

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# Distal zone must exceed proximal whiteness by at least this fraction to indicate
# localized separation rather than generalized whitening.
ONYCHOLYSIS_EXCESS_THRESHOLD = 0.3

# Distal region must be sufficiently white before the excess is evaluated.
ONYCHOLYSIS_DISTAL_WHITE_GATE = 0.4


def measure(region):
    """Return (distal_white_frac, excess).

    distal_white_frac: fraction of non-NaN distal cells (last 1/3) where V > ONYCHOLYSIS_V_MIN and S < ONYCHOLYSIS_S_MAX.
    excess: distal_white_frac - prox_white_frac (how much more white the distal end is).
    """
    grid_v = region["grid_v"]
    grid_s = region["grid_s"]

    # Split into proximal (0 to 2/3 of nail length) and distal (2/3 to 100%).
    distal_idx = int(2 / 3 * GRID_H)
    grid_v_distal = grid_v[distal_idx:]
    grid_s_distal = grid_s[distal_idx:]
    grid_v_prox = grid_v[:distal_idx]
    grid_s_prox = grid_s[:distal_idx]

    # Distal white fraction: count cells where V > threshold and S < threshold.
    white_cells_distal = (grid_v_distal > ONYCHOLYSIS_V_MIN) & (grid_s_distal < ONYCHOLYSIS_S_MAX)
    non_nan_cells_distal = ~np.isnan(grid_v_distal)
    if non_nan_cells_distal.sum() == 0:
        distal_white_frac = 0.0
    else:
        distal_white_frac = float(white_cells_distal.sum() / non_nan_cells_distal.sum())

    # Proximal white fraction: same metric over the proximal two-thirds.
    white_cells_prox = (grid_v_prox > ONYCHOLYSIS_V_MIN) & (grid_s_prox < ONYCHOLYSIS_S_MAX)
    non_nan_cells_prox = ~np.isnan(grid_v_prox)
    if non_nan_cells_prox.sum() == 0:
        prox_white_frac = 0.0
    else:
        prox_white_frac = float(white_cells_prox.sum() / non_nan_cells_prox.sum())

    # Excess: how much whiter the distal zone is than the rest.
    excess = distal_white_frac - prox_white_frac

    return distal_white_frac, excess


def to_verdict(distal_white_frac, excess):
    """Return "outside" if both whiteness and excess thresholds are met, else "within"."""
    if distal_white_frac > ONYCHOLYSIS_DISTAL_WHITE_GATE and excess > ONYCHOLYSIS_EXCESS_THRESHOLD:
        return "outside"
    return "within"


def build_finding(region):
    distal_white_frac, excess = measure(region)
    return {
        "label": "onycholysis",
        "display_name": "Nail separation (onycholysis)",
        "value": None,
        "unit": None,
        "verdict": to_verdict(distal_white_frac, excess),
        "confidence": heuristic_confidence(excess, ONYCHOLYSIS_EXCESS_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "onycholysis",
        "display_name": "Nail separation (onycholysis)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
