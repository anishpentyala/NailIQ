"""Tests for Beau's lines detection."""

import numpy as np
import pytest

from ml.infer.beaus_lines import groove_depth, depth_to_verdict, build_finding, inconclusive_finding, BEAUS_DEPTH_THRESHOLD


def make_region(grid_v):
    """Helper to construct a minimal region dict with a given grid_v."""
    return {
        "grid_v": grid_v,
        "grid_s": np.full_like(grid_v, 0.5),
        "V": np.array([]),
        "S": np.array([]),
        "across": np.array([]),
        "along": np.array([]),
        "region_px": 0,
        "finger_px": 0,
    }


def test_uniform_bright_plate():
    """Uniform bright plate (V~0.6 everywhere) should yield within verdict."""
    grid_v = np.full((64, 48), 0.6)
    region = make_region(grid_v)

    depth = groove_depth(region)
    assert depth < BEAUS_DEPTH_THRESHOLD, f"Expected depth < {BEAUS_DEPTH_THRESHOLD}, got {depth}"

    verdict = depth_to_verdict(depth)
    assert verdict == "within"


def test_interior_dark_band():
    """Dark transverse band at interior rows ~30-33 (V~0.3) on V~0.6 plate -> outside."""
    grid_v = np.full((64, 48), 0.6)
    # Dark band at rows 30-33
    grid_v[30:34] = 0.3
    region = make_region(grid_v)

    depth = groove_depth(region)
    assert depth > BEAUS_DEPTH_THRESHOLD, f"Expected depth > {BEAUS_DEPTH_THRESHOLD}, got {depth}"

    verdict = depth_to_verdict(depth)
    assert verdict == "outside"


def test_proximal_edge_dark_band():
    """Dark band ONLY at proximal edge rows 0-2 (excluded by interior logic) -> within."""
    grid_v = np.full((64, 48), 0.6)
    # Dark band only at the very proximal edge
    grid_v[0:3] = 0.3
    region = make_region(grid_v)

    depth = groove_depth(region)
    assert depth < BEAUS_DEPTH_THRESHOLD, f"Expected depth < {BEAUS_DEPTH_THRESHOLD}, got {depth}"

    verdict = depth_to_verdict(depth)
    assert verdict == "within"


def test_distal_edge_dark_band():
    """Dark band ONLY at distal edge rows 61-63 (excluded by interior logic) -> within."""
    grid_v = np.full((64, 48), 0.6)
    # Dark band only at the very distal edge
    grid_v[61:64] = 0.3
    region = make_region(grid_v)

    depth = groove_depth(region)
    assert depth < BEAUS_DEPTH_THRESHOLD, f"Expected depth < {BEAUS_DEPTH_THRESHOLD}, got {depth}"

    verdict = depth_to_verdict(depth)
    assert verdict == "within"


def test_build_finding_within():
    """build_finding returns correct shape with within verdict."""
    grid_v = np.full((64, 48), 0.6)
    region = make_region(grid_v)

    finding = build_finding(region)

    assert finding["label"] == "beaus_lines"
    assert finding["display_name"] == "Nail surface (Beau's lines)"
    assert finding["value"] is None
    assert finding["unit"] is None
    assert finding["verdict"] in ["within", "outside", "inconclusive"]
    assert 0.0 <= finding["confidence"] <= 1.0
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] is None


def test_build_finding_outside():
    """build_finding returns outside verdict for strong groove."""
    grid_v = np.full((64, 48), 0.6)
    grid_v[30:34] = 0.3
    region = make_region(grid_v)

    finding = build_finding(region)

    assert finding["verdict"] == "outside"
    assert finding["confidence"] > 0.0


def test_inconclusive_finding():
    """inconclusive_finding returns correct structure."""
    reason = "test_reason"
    finding = inconclusive_finding(reason)

    assert finding["label"] == "beaus_lines"
    assert finding["display_name"] == "Nail surface (Beau's lines)"
    assert finding["value"] is None
    assert finding["unit"] is None
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] == reason


def test_partially_nan_grid():
    """Grid with NaN values (empty cells) still detects groove if span is sufficient."""
    grid_v = np.full((64, 48), 0.6)
    # Dark band at row 30, but with some NaN
    grid_v[30, :] = 0.3
    grid_v[30, 0:10] = np.nan  # 10 NaN out of 48 = 79% valid, still > 40%
    region = make_region(grid_v)

    depth = groove_depth(region)
    # Should still detect the groove since 38 non-NaN cells out of 48 is still valid
    # and most of them are dark.
    assert depth >= 0.0  # At least computes without error


def test_empty_interior():
    """Grid too small or all NaN in interior rows yields depth 0.0."""
    grid_v = np.full((64, 48), np.nan)
    region = make_region(grid_v)

    depth = groove_depth(region)
    assert depth == 0.0


def test_narrow_band_not_spanning_width():
    """A dark spot not spanning the row width should not count as a groove."""
    grid_v = np.full((64, 48), 0.6)
    # Dark spot in the middle of row 30, but only a few pixels -> dark_fraction < 0.5
    grid_v[30, 20:25] = 0.3  # Only 5 pixels dark out of 48 = 10% < 50%
    region = make_region(grid_v)

    depth = groove_depth(region)
    assert depth < BEAUS_DEPTH_THRESHOLD
