"""Melanonychia (a dark longitudinal pigment band in the nail) -- color track,
top-down photo.

Classical CV like the geometry conditions. Within the nail region (nail_region.py)
a melanonychia band shows up as a stripe of pixels, running along the nail, that is
much darker than the rest of the plate. We bin the region across its width and look
for an *internal* bin (not the outermost ones, which catch finger/nail-edge shadow)
whose median brightness is well below the region's. No trained model needed.
"""

import numpy as np

from .nail_region import NAIL_WIDTH_FRAC, heuristic_confidence

NUM_ACROSS_BINS = 11
EDGE_BINS_EXCLUDED = 2  # drop the outermost bins each side (edge shadow, not pigment)

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# How much darker than the rest of the plate an internal stripe must be (as a
# fraction of the region's median brightness) to be flagged.
BAND_CONTRAST_THRESHOLD = 0.40


def band_contrast(region):
    """Relative darkness of the darkest internal across-bin vs the region median."""
    V = region["V"]
    across = region["across"]
    n = V.size
    if n == 0:
        return 0.0
    region_med = float(np.median(V))
    if region_med <= 1e-6:
        return 0.0

    # Map across (-NAIL_WIDTH_FRAC..NAIL_WIDTH_FRAC) onto bin indices.
    span = 2 * NAIL_WIDTH_FRAC
    bins = np.clip(((across + NAIL_WIDTH_FRAC) / span * NUM_ACROSS_BINS).astype(int),
                   0, NUM_ACROSS_BINS - 1)

    min_bin_px = max(20, int(0.02 * n))
    darkest = region_med
    for b in range(EDGE_BINS_EXCLUDED, NUM_ACROSS_BINS - EDGE_BINS_EXCLUDED):
        sel = bins == b
        if int(sel.sum()) >= min_bin_px:
            darkest = min(darkest, float(np.median(V[sel])))

    return (region_med - darkest) / region_med


# Darker skin (low ITA) commonly has benign longitudinal melanonychia, so we demand
# a stronger band before flagging it -- judging it by the same threshold as light
# skin would over-flag exactly the population in whom it's usually normal. ITA < 28
# is the standard "tan and darker" boundary (Chardon 1991).
DARK_SKIN_ITA = 28.0
DARK_SKIN_THRESHOLD_BUMP = 0.20


def tone_adjusted_threshold(skin_ita):
    if skin_ita is not None and skin_ita < DARK_SKIN_ITA:
        return BAND_CONTRAST_THRESHOLD + DARK_SKIN_THRESHOLD_BUMP
    return BAND_CONTRAST_THRESHOLD


def contrast_to_verdict(contrast, skin_ita=None):
    return "outside" if contrast > tone_adjusted_threshold(skin_ita) else "within"


def build_finding(region):
    contrast = band_contrast(region)
    skin_ita = region.get("skin_ita")
    threshold = tone_adjusted_threshold(skin_ita)
    return {
        "label": "melanonychia",
        "display_name": "Nail pigmentation (melanonychia)",
        "value": None,
        "unit": None,
        "verdict": contrast_to_verdict(contrast, skin_ita),
        "confidence": heuristic_confidence(contrast, threshold),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "melanonychia",
        "display_name": "Nail pigmentation (melanonychia)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
