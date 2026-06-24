"""Tests for splinter_hemorrhages.py

Synthetic region dicts with numpy grid_v arrays to verify the streak detection
logic without needing photos or the full contour pipeline.
"""

import numpy as np
import pytest

from ml.infer.splinter_hemorrhages import (
    count_streaks,
    count_to_verdict,
    build_finding,
    inconclusive_finding,
    SPLINTER_COUNT_THRESHOLD,
)

# Constants from nail_region.py
GRID_H = 64
GRID_W = 48


def make_region(grid_v, grid_s=None):
    """Helper: build a minimal region dict with grid_v and grid_s."""
    if grid_s is None:
        grid_s = np.full((GRID_H, GRID_W), np.nan)
    return {
        "grid_v": grid_v,
        "grid_s": grid_s,
        "S": np.array([]),
        "V": np.array([]),
        "across": np.array([]),
        "along": np.array([]),
        "region_px": 0,
        "finger_px": 0,
    }


def test_clean_bright_plate():
    """Test case (a): clean bright nail plate with no dark streaks -> within."""
    grid_v = np.full((GRID_H, GRID_W), 0.6, dtype=np.float64)  # uniform bright
    region = make_region(grid_v)

    streak_count = count_streaks(region)
    assert streak_count == 0, "Clean plate should have 0 streaks"

    verdict = count_to_verdict(streak_count)
    assert verdict == "within", "0 streaks -> within"

    finding = build_finding(region)
    assert finding["verdict"] == "within"
    assert finding["label"] == "splinter_hemorrhages"
    assert finding["track_used"] == "color"


def test_two_thin_vertical_streaks():
    """Test case (b): TWO thin vertical dark streaks on a bright plate -> outside."""
    grid_v = np.full((GRID_H, GRID_W), 0.6, dtype=np.float64)

    # Streak 1: column 12, rows 20..30 (height 11, width 1)
    grid_v[20:31, 12] = 0.2

    # Streak 2: column 30, rows 20..30 (height 11, width 1)
    grid_v[20:31, 30] = 0.2

    region = make_region(grid_v)
    streak_count = count_streaks(region)
    assert streak_count >= 2, f"Expected >=2 streaks, got {streak_count}"

    verdict = count_to_verdict(streak_count)
    assert verdict == "outside", ">=2 streaks -> outside"

    finding = build_finding(region)
    assert finding["verdict"] == "outside"
    assert finding["confidence"] > 0.0, "Non-zero confidence for detected streaks"


def test_single_wide_dark_blob():
    """Test case (c): a single wide dark blob (rows 20..30, cols 10..30) -> within.

    This fails the aspect ratio test (wide, not elongated vertically) and/or size
    test, so it should not count as a splinter streak.
    """
    grid_v = np.full((GRID_H, GRID_W), 0.6, dtype=np.float64)

    # Wide blob: rows 20..30 (height 11), cols 10..30 (width 21)
    grid_v[20:31, 10:31] = 0.2

    region = make_region(grid_v)
    streak_count = count_streaks(region)
    # Wide blob should fail h >= 2*w (11 < 2*21 = 42) or exceed max area
    assert streak_count == 0, f"Wide blob should not count as streak, got {streak_count}"

    verdict = count_to_verdict(streak_count)
    assert verdict == "within", "0 streaks -> within"

    finding = build_finding(region)
    assert finding["verdict"] == "within"


def test_empty_region():
    """Test with all-NaN grid (empty region) -> should not crash, return 0 streaks."""
    grid_v = np.full((GRID_H, GRID_W), np.nan)
    region = make_region(grid_v)

    streak_count = count_streaks(region)
    assert streak_count == 0, "Empty region should have 0 streaks"

    verdict = count_to_verdict(streak_count)
    assert verdict == "within"


def test_inconclusive_finding():
    """Test inconclusive_finding factory."""
    finding = inconclusive_finding("nail_region_unclear")
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["failure_reason"] == "nail_region_unclear"
    assert finding["label"] == "splinter_hemorrhages"
    assert finding["track_used"] == "color"


def test_threshold_boundary():
    """Test the threshold: exactly 1 streak should be within, 2+ should be outside."""
    grid_v = np.full((GRID_H, GRID_W), 0.6, dtype=np.float64)

    # Add exactly 1 streak
    grid_v[20:31, 12] = 0.2
    region = make_region(grid_v)
    streak_count = count_streaks(region)
    assert streak_count == 1, "Should count 1 streak"

    verdict = count_to_verdict(streak_count)
    assert verdict == "within", "1 streak <= threshold -> within"

    # Now add a second streak
    grid_v[20:31, 30] = 0.2
    region = make_region(grid_v)
    streak_count = count_streaks(region)
    assert streak_count >= 2, "Should count >=2 streaks"

    verdict = count_to_verdict(streak_count)
    assert verdict == "outside", ">=2 streaks > threshold -> outside"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
