"""Tests for the pitting detector."""

import numpy as np
import pytest

from ml.infer.pitting import build_finding, inconclusive_finding, count_pits


def make_region(grid_v, grid_s=None):
    """Helper to build a minimal region dict for testing."""
    if grid_s is None:
        grid_s = np.full_like(grid_v, np.nan)
    return {
        "grid_v": grid_v,
        "grid_s": grid_s,
        "V": grid_v.flatten(),
        "S": grid_s.flatten(),
        "across": np.zeros(grid_v.size),
        "along": np.zeros(grid_v.size),
        "region_px": np.sum(~np.isnan(grid_v)),
        "finger_px": 1000,
    }


def test_smooth_bright_plate_no_pits():
    """Smooth, bright nail plate (V~0.6) should have no pits -> within."""
    grid_v = np.full((64, 48), 0.6)
    region = make_region(grid_v)

    pit_count = count_pits(region)
    assert pit_count == 0

    finding = build_finding(region)
    assert finding["verdict"] == "within"
    assert finding["label"] == "pitting"
    assert finding["display_name"] == "Nail surface (pitting)"
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] is None


def test_five_small_dark_pits_scattered():
    """Five small (2x2 cells), roundish dark pits (V~0.2) on bright plate (V~0.6) -> outside."""
    grid_v = np.full((64, 48), 0.6)

    # Create five 2x2 dark pits scattered across the nail.
    pit_locations = [(10, 10), (25, 20), (40, 15), (50, 35), (30, 45)]
    for row, col in pit_locations:
        if row + 2 < 64 and col + 2 < 48:
            grid_v[row : row + 2, col : col + 2] = 0.2

    region = make_region(grid_v)

    pit_count = count_pits(region)
    # Five 2x2 pits should each be counted (area 4 pixels each, well within criteria).
    assert pit_count >= 4, f"Expected at least 4 pits, got {pit_count}"

    finding = build_finding(region)
    assert finding["verdict"] == "outside", f"Expected 'outside', got '{finding['verdict']}'"
    assert finding["confidence"] > 0.4


def test_two_small_dark_pits_below_threshold():
    """Two small dark pits (below the >=4 gate) -> within."""
    grid_v = np.full((64, 48), 0.6)

    # Create only two 2x2 dark pits.
    pit_locations = [(10, 10), (40, 35)]
    for row, col in pit_locations:
        if row + 2 < 64 and col + 2 < 48:
            grid_v[row : row + 2, col : col + 2] = 0.2

    region = make_region(grid_v)

    pit_count = count_pits(region)
    # Two pits, should be <= threshold (3.5).
    assert pit_count <= 3, f"Expected at most 3 pits, got {pit_count}"

    finding = build_finding(region)
    assert finding["verdict"] == "within"


def test_inconclusive_finding():
    """Test inconclusive_finding factory."""
    finding = inconclusive_finding("nail_region_unclear")
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["failure_reason"] == "nail_region_unclear"
    assert finding["label"] == "pitting"
    assert finding["track_used"] == "color"
