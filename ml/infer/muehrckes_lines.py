"""Muehrcke's lines (paired white transverse bands running across the nail,
parallel to the cuticle) -- color track, top-down photo.

Classical CV like the other color conditions. Within the nail region (nail_region.py)
Muehrcke's lines appear as two or more bright transverse bands running horizontally
across the nail width. The key feature is that they are white (high brightness, low
saturation) and appear in characteristic pairs.

No trained model needed.
"""

import warnings

import numpy as np

from .nail_region import GRID_H, GRID_W, heuristic_confidence

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# How much brighter than the region baseline an interior row must be (as a fraction)
# to be flagged as a white band.
MUEHRCKE_BRIGHT_THRESHOLD = 0.12

# Maximum saturation allowed for a row to be considered white (low S).
MUEHRCKE_SAT_MAX = 0.25

# Muehrcke's lines are characteristically paired (two bands); need at least 1.5 bands
# to call it "outside typical range" (i.e., >= 2 bands detected).
MUEHRCKE_BAND_COUNT_THRESHOLD = 1.5


def count_bands(region):
    """Count the number of bright white transverse bands in the nail region.

    A band is one or more adjacent rows where:
    - The row is valid (has >= 40% non-NaN cells).
    - Interior rows only (exclude proximal/distal 10%).
    - Row brightness is significantly above the baseline (>= MUEHRCKE_BRIGHT_THRESHOLD).
    - Row spans the nail width (>= 50% of non-NaN cells are bright).
    - Row is low saturation (< MUEHRCKE_SAT_MAX).

    Adjacent qualifying rows are grouped into a single band. Returns the number of
    distinct bands found.
    """
    grid_v = region["grid_v"]
    grid_s = region["grid_s"]

    # Compute mean brightness per row, silencing the harmless "Mean of empty slice"
    # warning from fully-empty rows at the region corners.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        row_mean_v = np.nanmean(grid_v, axis=1)
        row_mean_s = np.nanmean(grid_s, axis=1)

    # A row is valid if it has >= 40% non-NaN cells.
    valid_cols_per_row = np.sum(~np.isnan(grid_v), axis=1)
    min_valid_cols = int(0.4 * GRID_W)
    is_valid = valid_cols_per_row >= min_valid_cols

    # Interior rows exclude the proximal-most and distal-most 10%.
    edge_rows = int(0.1 * GRID_H)
    interior_mask = np.zeros(GRID_H, dtype=bool)
    interior_mask[edge_rows : GRID_H - edge_rows] = True

    interior_rows = is_valid & interior_mask
    if not np.any(interior_rows):
        return 0

    # Baseline brightness over valid interior rows.
    baseline = float(np.nanmedian(row_mean_v[interior_rows]))
    if baseline <= 1e-6:
        return 0

    # Mark rows that qualify as bright white bands.
    is_bright_band = np.zeros(GRID_H, dtype=bool)
    for r in range(GRID_H):
        if not (is_valid[r] and interior_mask[r]):
            continue

        # Check: row is bright (>= baseline + threshold).
        if row_mean_v[r] < baseline * (1.0 + MUEHRCKE_BRIGHT_THRESHOLD):
            continue

        # Check: row spans the width (>= 50% of non-NaN cells are bright).
        row_vals = grid_v[r]
        non_nan_mask = ~np.isnan(row_vals)
        if not np.any(non_nan_mask):
            continue

        non_nan_vals = row_vals[non_nan_mask]
        bright_threshold = 1.10 * baseline
        bright_count = np.sum(non_nan_vals > bright_threshold)
        bright_fraction = bright_count / np.sum(non_nan_mask)

        if bright_fraction < 0.5:
            continue

        # Check: row is low saturation.
        if row_mean_s[r] >= MUEHRCKE_SAT_MAX:
            continue

        is_bright_band[r] = True

    # Group adjacent bright rows into bands.
    band_count = 0
    in_band = False
    for r in range(GRID_H):
        if is_bright_band[r]:
            if not in_band:
                band_count += 1
                in_band = True
        else:
            in_band = False

    return band_count


def count_to_verdict(band_count):
    return "outside" if band_count > MUEHRCKE_BAND_COUNT_THRESHOLD else "within"


def build_finding(region):
    band_count = count_bands(region)
    return {
        "label": "muehrckes_lines",
        "display_name": "Nail markings (Muehrcke's lines)",
        "value": None,
        "unit": None,
        "verdict": count_to_verdict(band_count),
        "confidence": heuristic_confidence(band_count, MUEHRCKE_BAND_COUNT_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "muehrckes_lines",
        "display_name": "Nail markings (Muehrcke's lines)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
