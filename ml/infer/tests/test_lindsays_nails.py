"""Tests for Lindsay's nails detection."""

import numpy as np
import pytest

from ml.infer import lindsays_nails


def test_uniform_pink_nail_within():
    """A uniform pink nail (V~0.6 everywhere) should be within typical range."""
    grid_v = np.full((64, 48), 0.6, dtype=np.float64)
    grid_s = np.full((64, 48), 0.5, dtype=np.float64)
    region = {"grid_v": grid_v, "grid_s": grid_s}

    prox_white_frac, contrast = lindsays_nails.measure(region)
    verdict = lindsays_nails.to_verdict(prox_white_frac, contrast)

    assert verdict == "within"
    assert prox_white_frac < 0.1  # Very few cells are white
    assert contrast < 0.05  # Minimal contrast


def test_half_and_half_nail_outside():
    """A half-and-half nail (proximal white V~0.9/S~0.05, distal dark V~0.55) should be outside."""
    grid_v = np.full((64, 48), 0.55, dtype=np.float64)
    grid_s = np.full((64, 48), 0.5, dtype=np.float64)

    # Proximal half: white and desaturated
    grid_v[:32, :] = 0.9
    grid_s[:32, :] = 0.05

    region = {"grid_v": grid_v, "grid_s": grid_s}

    prox_white_frac, contrast = lindsays_nails.measure(region)
    verdict = lindsays_nails.to_verdict(prox_white_frac, contrast)

    assert verdict == "outside"
    assert prox_white_frac > 0.9  # Almost all proximal cells are white
    assert contrast > 0.30  # Strong contrast (0.9 - 0.55 = 0.35)


def test_proximal_not_white_within():
    """Proximal NOT white (V~0.6) with a darker distal (V~0.4) should be within (white gate fails)."""
    grid_v = np.full((64, 48), 0.4, dtype=np.float64)
    grid_s = np.full((64, 48), 0.5, dtype=np.float64)

    # Proximal half: NOT white (low V)
    grid_v[:32, :] = 0.6
    grid_s[:32, :] = 0.5  # Still saturated

    region = {"grid_v": grid_v, "grid_s": grid_s}

    prox_white_frac, contrast = lindsays_nails.measure(region)
    verdict = lindsays_nails.to_verdict(prox_white_frac, contrast)

    assert verdict == "within"
    assert prox_white_frac < 0.1  # Proximal cells don't meet the white criterion
    # Even though contrast might exist, the white gate blocks the outside verdict


def test_build_finding_integration():
    """Test that build_finding integrates measure and to_verdict correctly."""
    grid_v = np.full((64, 48), 0.55, dtype=np.float64)
    grid_s = np.full((64, 48), 0.5, dtype=np.float64)
    grid_v[:32, :] = 0.9
    grid_s[:32, :] = 0.05

    region = {"grid_v": grid_v, "grid_s": grid_s}
    finding = lindsays_nails.build_finding(region)

    assert finding["label"] == "lindsays_nails"
    assert finding["display_name"] == "Nail color (half-and-half nails)"
    assert finding["verdict"] == "outside"
    assert finding["value"] is None
    assert finding["unit"] is None
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] is None
    assert 0.0 <= finding["confidence"] <= 1.0


def test_inconclusive_finding():
    """Test that inconclusive_finding has the correct structure."""
    finding = lindsays_nails.inconclusive_finding("test_failure")

    assert finding["label"] == "lindsays_nails"
    assert finding["display_name"] == "Nail color (half-and-half nails)"
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] == "test_failure"


def test_nan_handling():
    """Test that the measure function handles NaN values gracefully."""
    grid_v = np.full((64, 48), np.nan, dtype=np.float64)
    grid_s = np.full((64, 48), np.nan, dtype=np.float64)

    region = {"grid_v": grid_v, "grid_s": grid_s}
    prox_white_frac, contrast = lindsays_nails.measure(region)

    assert prox_white_frac == 0.0
    assert contrast == 0.0
