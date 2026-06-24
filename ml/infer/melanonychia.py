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


def contrast_to_verdict(contrast):
    return "outside" if contrast > BAND_CONTRAST_THRESHOLD else "within"


def build_finding(region):
    contrast = band_contrast(region)
    return {
        "label": "melanonychia",
        "display_name": "Nail pigmentation (melanonychia)",
        "value": None,
        "unit": None,
        "verdict": contrast_to_verdict(contrast),
        "confidence": heuristic_confidence(contrast, BAND_CONTRAST_THRESHOLD),
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
