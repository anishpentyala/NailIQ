"""Tests for the Terry's nails detector."""

import numpy as np
import pytest
from ml.infer.terrys_nails import (
    build_finding,
    measure,
    to_verdict,
    TERRYS_CONTRAST_THRESHOLD,
    TERRYS_WHITE_FRAC_GATE,
    TERRYS_V_MIN,
    TERRYS_S_MAX,
)
from ml.infer.nail_region import GRID_H, GRID_W


def make_region(grid_v, grid_s):
    """Helper to construct a region dict with numpy grids."""
    return {
        "grid_v": grid_v,
        "grid_s": grid_s,
        "S": np.array([]),
        "V": np.array([]),
        "across": np.array([]),
        "along": np.array([]),
        "region_px": 1000,
        "finger_px": 5000,
    }


def test_uniform_pink_nail_within():
    """A uniform pink nail (V~0.6, S~0.3) should be within typical range."""
    grid_v = np.full((GRID_H, GRID_W), 0.6)
    grid_s = np.full((GRID_H, GRID_W), 0.3)
    region = make_region(grid_v, grid_s)

    prox_white_frac, band_contrast = measure(region)
    verdict = to_verdict(prox_white_frac, band_contrast)

    # Pink is not white enough (doesn't meet white gate), so should be within.
    assert verdict == "within"
    assert prox_white_frac < TERRYS_WHITE_FRAC_GATE


def test_terrys_pattern_outside():
    """A Terry's pattern (proximal white V~0.9/S~0.05, distal dark V~0.6) should be outside."""
    grid_v = np.full((GRID_H, GRID_W), np.nan)
    grid_s = np.full((GRID_H, GRID_W), np.nan)

    # Proximal 80% rows: white
    prox_idx = int(0.8 * GRID_H)
    grid_v[:prox_idx, :] = 0.9
    grid_s[:prox_idx, :] = 0.05

    # Distal 20% rows: darker
    grid_v[prox_idx:, :] = 0.6
    grid_s[prox_idx:, :] = 0.15

    region = make_region(grid_v, grid_s)
    prox_white_frac, band_contrast = measure(region)
    verdict = to_verdict(prox_white_frac, band_contrast)

    # Proximal is white and distal is dark -> should be outside.
    assert verdict == "outside"
    assert prox_white_frac > TERRYS_WHITE_FRAC_GATE
    assert band_contrast > TERRYS_CONTRAST_THRESHOLD


def test_proximal_not_white_within():
    """Proximal nail pink (V~0.6, S~0.3) even with a darker distal band -> within."""
    grid_v = np.full((GRID_H, GRID_W), np.nan)
    grid_s = np.full((GRID_H, GRID_W), np.nan)

    # Proximal 80% rows: pink, not white
    prox_idx = int(0.8 * GRID_H)
    grid_v[:prox_idx, :] = 0.6
    grid_s[:prox_idx, :] = 0.3

    # Distal 20% rows: darker
    grid_v[prox_idx:, :] = 0.4
    grid_s[prox_idx:, :] = 0.25

    region = make_region(grid_v, grid_s)
    prox_white_frac, band_contrast = measure(region)
    verdict = to_verdict(prox_white_frac, band_contrast)

    # White gate fails (proximal is pink, not white) even with contrast -> within.
    assert verdict == "within"
    assert prox_white_frac < TERRYS_WHITE_FRAC_GATE


def test_finding_dict_structure():
    """Verify build_finding returns the correct dict shape."""
    grid_v = np.full((GRID_H, GRID_W), 0.6)
    grid_s = np.full((GRID_H, GRID_W), 0.3)
    region = make_region(grid_v, grid_s)

    finding = build_finding(region)

    assert finding["label"] == "terrys_nails"
    assert finding["display_name"] == "Nail color (Terry's nails)"
    assert finding["value"] is None
    assert finding["unit"] is None
    assert finding["verdict"] in ["within", "outside", "inconclusive"]
    assert 0.0 <= finding["confidence"] <= 1.0
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] is None
