"""Splinter hemorrhages (small dark longitudinal streaks in the nail) -- color track, top-down photo.

Classical CV like the color-track conditions: from the nail region (nail_region.py)
we detect dark vertical streaks in the grid and flag the presence of multiple
streaks as outside typical range. No trained model needed.

A splinter streak is a thin dark line running along the length of the nail (rows),
not a blob or wide discoloration. We detect them by finding connected components of
dark pixels, then filtering to those that are vertically elongated and small.
"""

import cv2
import numpy as np

from .nail_region import heuristic_confidence

# Detection thresholds for dark pixels in the grid.
# A pixel is dark if its Value is significantly below the plate median.
DARK_SIGMA_FACTOR = 1.5
DARK_VALUE_FRAC = 0.8

# Size constraints for a valid splinter component.
# Must be small (not a blob), but tall (vertically elongated).
MIN_COMPONENT_AREA = 2
MAX_COMPONENT_AREA_FRAC = 0.04  # relative to GRID_H * GRID_W
MIN_COMPONENT_HEIGHT = 3
HEIGHT_TO_WIDTH_RATIO = 2.0  # h >= 2*w to be a vertical streak

# Rough starting estimate -- requires >=2 clear streaks to flag, to limit false
# positives; no labeled dataset yet.
SPLINTER_COUNT_THRESHOLD = 1.5


def count_streaks(region):
    """Count the number of dark vertical streak components in the nail region grid.

    Args:
        region: dict with "grid_v" (GRID_H x GRID_W array of Value, NaN where empty)

    Returns:
        int: number of components that qualify as splinter streaks
    """
    grid_v = region["grid_v"]
    GRID_H, GRID_W = grid_v.shape

    # Valid cells: not NaN
    valid = ~np.isnan(grid_v)
    if valid.sum() == 0:
        return 0

    # Dark pixel detection: below median and below a fraction of median
    med = np.nanmedian(grid_v)
    std = np.nanstd(grid_v)
    dark = valid & (grid_v < med - DARK_SIGMA_FACTOR * std) & (grid_v < DARK_VALUE_FRAC * med)
    mask = dark.astype(np.uint8) * 255

    # Connected components analysis
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    streak_count = 0
    max_area = int(MAX_COMPONENT_AREA_FRAC * GRID_H * GRID_W)

    for i in range(1, n):  # skip background (i=0)
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])

        # Qualify as a splinter streak if small, tall, and vertically elongated
        if (area >= MIN_COMPONENT_AREA and
            area <= max_area and
            h >= MIN_COMPONENT_HEIGHT and
            h >= HEIGHT_TO_WIDTH_RATIO * w):
            streak_count += 1

    return streak_count


def count_to_verdict(n):
    """Convert streak count to verdict.

    Args:
        n: int, number of streaks detected

    Returns:
        str: "outside" if n > threshold, else "within"
    """
    return "outside" if n > SPLINTER_COUNT_THRESHOLD else "within"


def build_finding(region):
    """Build a splinter hemorrhages finding from a nail region grid.

    Args:
        region: dict from nail_region.compute_nail_region()

    Returns:
        dict: finding with label, verdict, confidence, etc.
    """
    streak_count = count_streaks(region)
    return {
        "label": "splinter_hemorrhages",
        "display_name": "Nail markings (splinter hemorrhages)",
        "value": None,
        "unit": None,
        "verdict": count_to_verdict(streak_count),
        "confidence": heuristic_confidence(streak_count, SPLINTER_COUNT_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    """Return an inconclusive finding for when the region can't be analyzed.

    Args:
        failure_reason: str, explanation of why the region was unusable

    Returns:
        dict: inconclusive finding
    """
    return {
        "label": "splinter_hemorrhages",
        "display_name": "Nail markings (splinter hemorrhages)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
