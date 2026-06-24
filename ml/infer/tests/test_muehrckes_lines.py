"""Tests for Muehrcke's lines detector."""

import numpy as np
import pytest

from ..muehrckes_lines import count_bands, count_to_verdict, build_finding


def _make_region(grid_v, grid_s):
    """Helper to create a minimal region dict."""
    return {
        "grid_v": grid_v,
        "grid_s": grid_s,
    }


def test_uniform_plate_no_bands():
    """Uniform nail plate with no bright bands -> within."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)
    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 0
    assert count_to_verdict(band_count) == "within"

    finding = build_finding(region)
    assert finding["verdict"] == "within"
    assert finding["label"] == "muehrckes_lines"
    assert finding["display_name"] == "Nail markings (Muehrcke's lines)"
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] is None


def test_two_separated_bright_bands():
    """Two separated bright white bands -> outside."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)

    # First bright band at rows 20-21 (interior, not edge).
    grid_v[20:22, :] = 0.85
    grid_s[20:22, :] = 0.1

    # Second bright band at rows 40-41 (interior, not edge).
    grid_v[40:42, :] = 0.85
    grid_s[40:42, :] = 0.1

    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 2, f"Expected 2 bands, got {band_count}"
    assert count_to_verdict(band_count) == "outside"

    finding = build_finding(region)
    assert finding["verdict"] == "outside"


def test_single_bright_band():
    """Single bright band -> within (below the >=2 gate for Muehrcke's)."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)

    # Single bright band at rows 30-31.
    grid_v[30:32, :] = 0.85
    grid_s[30:32, :] = 0.1

    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 1, f"Expected 1 band, got {band_count}"
    assert count_to_verdict(band_count) == "within"

    finding = build_finding(region)
    assert finding["verdict"] == "within"


def test_edge_rows_excluded():
    """Bands at the proximal/distal 10% edges are excluded (lunula/free edge)."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)

    # Try to put bands at the edges; they should be ignored.
    edge_rows = int(0.1 * 64)  # 6 rows
    grid_v[0:2, :] = 0.85  # Proximal edge
    grid_s[0:2, :] = 0.1
    grid_v[62:64, :] = 0.85  # Distal edge
    grid_s[62:64, :] = 0.1

    # Interior band that counts.
    grid_v[32:34, :] = 0.85
    grid_s[32:34, :] = 0.1

    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 1, f"Expected 1 interior band (edge bands excluded), got {band_count}"


def test_high_saturation_rows_ignored():
    """Rows with high saturation are not white; ignored."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)

    # Bright but high-saturation row (colored, not white).
    grid_v[25:27, :] = 0.85
    grid_s[25:27, :] = 0.5  # Too saturated

    # Bright low-saturation row (white).
    grid_v[40:42, :] = 0.85
    grid_s[40:42, :] = 0.1

    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 1, f"Expected 1 band (high-sat row ignored), got {band_count}"


def test_row_with_insufficient_width_span():
    """A bright low-sat row that doesn't span the width is ignored."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)

    # Narrow bright row (doesn't span >= 50% width).
    grid_v[25, 0:10] = 0.85
    grid_s[25, 0:10] = 0.1

    # Full-width bright low-sat band.
    grid_v[40:42, :] = 0.85
    grid_s[40:42, :] = 0.1

    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 1, f"Expected 1 full-width band (narrow row ignored), got {band_count}"


def test_adjacent_rows_form_one_band():
    """Adjacent bright rows group into a single band."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.3, dtype=np.float64)

    # Contiguous bright rows 30-34 form ONE band.
    grid_v[30:35, :] = 0.85
    grid_s[30:35, :] = 0.1

    # Separated bright rows 45-47 form another band.
    grid_v[45:48, :] = 0.85
    grid_s[45:48, :] = 0.1

    region = _make_region(grid_v, grid_s)

    band_count = count_bands(region)
    assert band_count == 2, f"Expected 2 bands (contiguous rows grouped), got {band_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
