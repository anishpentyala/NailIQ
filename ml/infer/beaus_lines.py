"""Beau's lines (transverse grooves running across the nail) -- color track,
top-down photo.

Classical CV like the other color conditions. Within the nail region (nail_region.py)
Beau's lines appear as a dark transverse band (a groove running horizontally across
the nail width). We examine the brightness per row and look for an internal row
(not the proximal/distal edges) whose brightness is well below the region baseline.
No trained model needed.
"""

import warnings

import numpy as np

from .nail_region import GRID_H, GRID_W, heuristic_confidence

# Rough starting estimate -- no labeled photo dataset yet to calibrate against.
# How much darker than the region baseline an interior row must be (as a fraction)
# to be flagged as a groove.
BEAUS_DEPTH_THRESHOLD = 0.18


def groove_depth(region):
    """Maximum groove depth among valid interior rows, or 0.0 if none found.

    A groove is a row spanning the nail width that is notably darker than the
    baseline brightness of interior rows.
    """
    grid_v = region["grid_v"]

    # Compute mean brightness per row (excluding NaN cells). Fully-empty rows
    # (NaN) are expected at the region corners and get filtered out below as
    # invalid -- silence the harmless "Mean of empty slice" warning they raise.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        row_mean = np.nanmean(grid_v, axis=1)

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
        return 0.0

    baseline = float(np.nanmedian(row_mean[interior_rows]))
    if baseline <= 1e-6:
        return 0.0

    max_groove = 0.0
    for r in range(GRID_H):
        if not (is_valid[r] and interior_mask[r]):
            continue

        # Check if this row spans the width: fraction of non-NaN cells
        # with value < 0.85*baseline must be >= 0.5.
        row_vals = grid_v[r]
        non_nan_mask = ~np.isnan(row_vals)
        if not np.any(non_nan_mask):
            continue

        non_nan_vals = row_vals[non_nan_mask]
        dark_threshold = 0.85 * baseline
        dark_count = np.sum(non_nan_vals < dark_threshold)
        dark_fraction = dark_count / np.sum(non_nan_mask)

        if dark_fraction >= 0.5:
            groove_d = (baseline - row_mean[r]) / baseline
            max_groove = max(max_groove, groove_d)

    return max_groove


def depth_to_verdict(depth):
    return "outside" if depth > BEAUS_DEPTH_THRESHOLD else "within"


def build_finding(region):
    depth = groove_depth(region)
    return {
        "label": "beaus_lines",
        "display_name": "Nail surface (Beau's lines)",
        "value": None,
        "unit": None,
        "verdict": depth_to_verdict(depth),
        "confidence": heuristic_confidence(depth, BEAUS_DEPTH_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "beaus_lines",
        "display_name": "Nail surface (Beau's lines)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
