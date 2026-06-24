"""Nail pitting (multiple small, roundish dark depressions on the nail plate) -- color track, top-down photo.

Classical CV like the geometry conditions: from the nail region (nail_region.py)
we detect and count small, roundish dark pits on the nail surface using connected-
component analysis on a Value-based dark threshold. No trained model needed.

A pit is identified as a connected component (8-connectivity) with area 1..~61 pixels
(max 2% of GRID_H x GRID_W), aspect ratio 0.5..2.0 (roundish), and max dimension <= 6
pixels. Four or more qualifying pits flags pitting as outside typical range.
"""

import numpy as np
import cv2

from .nail_region import heuristic_confidence, GRID_H, GRID_W

# Rough starting estimate -- requires >=4 small pits to flag, to limit false
# positives; no labeled dataset yet to calibrate against.
PITTING_COUNT_THRESHOLD = 3.5


def count_pits(region):
    """Count small, roundish, dark pits on the nail surface.

    Returns the number of qualifying pit components found in region["grid_v"].
    """
    grid_v = region["grid_v"]
    valid = ~np.isnan(grid_v)

    if not valid.any():
        return 0

    # Estimate baseline and variability of the nail plate.
    med = np.nanmedian(grid_v)
    std = np.nanstd(grid_v)

    if std == 0:
        return 0

    # Dark mask: pixels significantly darker than the median plate value.
    # Both relative to median (< med - 1.5*std) and absolute (< 0.8*med).
    dark_mask = valid & (grid_v < med - 1.5 * std) & (grid_v < 0.8 * med)
    dark_mask_uint8 = dark_mask.astype(np.uint8) * 255

    # Connected-component analysis to isolate individual pits.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(
        dark_mask_uint8, connectivity=8
    )

    pit_count = 0
    for i in range(1, n):  # skip background (component 0)
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]

        # Criteria for a pit:
        # - area >= 1 (non-empty)
        # - area <= ~2% of grid size (small, not a large dark region)
        # - roundish: aspect ratio 0.5..2.0 (not elongated)
        # - max extent <= 6 pixels (fits in a small bounding box)
        max_area = int(0.02 * GRID_H * GRID_W)
        aspect_ratio = h / max(w, 1)
        if (
            area >= 1
            and area <= max_area
            and 0.5 <= aspect_ratio <= 2.0
            and w <= 6
            and h <= 6
        ):
            pit_count += 1

    return pit_count


def count_to_verdict(pit_count):
    """Map pit count to a verdict."""
    return "outside" if pit_count > PITTING_COUNT_THRESHOLD else "within"


def build_finding(region):
    """Build a pitting finding from a nail region dict."""
    pit_count = count_pits(region)
    verdict = count_to_verdict(pit_count)
    confidence = heuristic_confidence(pit_count, PITTING_COUNT_THRESHOLD)

    return {
        "label": "pitting",
        "display_name": "Nail surface (pitting)",
        "value": None,
        "unit": None,
        "verdict": verdict,
        "confidence": confidence,
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    """Build an inconclusive pitting finding."""
    return {
        "label": "pitting",
        "display_name": "Nail surface (pitting)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
