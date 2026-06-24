"""Tests for onycholysis.py: synthetic regions covering uniform pink nails, distal-white
separation, and generalized whiteness."""

import numpy as np
import pytest
from ml.infer import onycholysis


def test_uniform_pink_nail():
    """Uniform pink nail (V~0.6, S~0.7) everywhere -> within."""
    grid_v = np.full((64, 48), 0.6)
    grid_s = np.full((64, 48), 0.7)
    region = {"grid_v": grid_v, "grid_s": grid_s}

    distal_white_frac, excess = onycholysis.measure(region)
    assert distal_white_frac < 0.05  # Nearly no white cells
    assert excess < 0.05  # No excess
    assert onycholysis.to_verdict(distal_white_frac, excess) == "within"


def test_distal_white_zone():
    """Distal third white (rows 43-63: V~0.9, S~0.05), rest pink (V~0.6, S~0.7) -> outside."""
    grid_v = np.full((64, 48), 0.6)
    grid_s = np.full((64, 48), 0.7)
    distal_start = int(2 / 3 * 64)  # row 42 (integer division)
    grid_v[distal_start:, :] = 0.9
    grid_s[distal_start:, :] = 0.05
    region = {"grid_v": grid_v, "grid_s": grid_s}

    distal_white_frac, excess = onycholysis.measure(region)
    assert distal_white_frac > 0.9  # Almost all distal cells are white
    assert excess > 0.8  # Large excess (distal much whiter than proximal)
    assert onycholysis.to_verdict(distal_white_frac, excess) == "outside"


def test_uniform_white_nail():
    """Uniform white nail everywhere (V~0.9, S~0.05) -> within (excess ~0, not distal-specific)."""
    grid_v = np.full((64, 48), 0.9)
    grid_s = np.full((64, 48), 0.05)
    region = {"grid_v": grid_v, "grid_s": grid_s}

    distal_white_frac, excess = onycholysis.measure(region)
    assert distal_white_frac > 0.9  # Distal is white
    assert abs(excess) < 0.1  # But proximal is equally white, so excess ~ 0
    assert onycholysis.to_verdict(distal_white_frac, excess) == "within"


def test_confidence_heuristic():
    """Confidence increases as excess grows past threshold."""
    grid_v = np.full((64, 48), 0.6)
    grid_s = np.full((64, 48), 0.7)
    distal_start = int(2 / 3 * 64)
    grid_v[distal_start:, :] = 0.9
    grid_s[distal_start:, :] = 0.05
    region = {"grid_v": grid_v, "grid_s": grid_s}

    _, excess = onycholysis.measure(region)
    confidence = onycholysis.heuristic_confidence(excess, onycholysis.ONYCHOLYSIS_EXCESS_THRESHOLD)
    assert 0.4 <= confidence <= 0.65  # Within the heuristic range


def test_build_finding_outside():
    """build_finding returns outside verdict with correct label and track_used."""
    grid_v = np.full((64, 48), 0.6)
    grid_s = np.full((64, 48), 0.7)
    distal_start = int(2 / 3 * 64)
    grid_v[distal_start:, :] = 0.9
    grid_s[distal_start:, :] = 0.05
    region = {"grid_v": grid_v, "grid_s": grid_s}

    finding = onycholysis.build_finding(region)
    assert finding["label"] == "onycholysis"
    assert finding["display_name"] == "Nail separation (onycholysis)"
    assert finding["verdict"] == "outside"
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] is None


def test_inconclusive_finding():
    """inconclusive_finding returns inconclusive verdict with the given failure reason."""
    failure_reason = "nail_region_unclear"
    finding = onycholysis.inconclusive_finding(failure_reason)
    assert finding["label"] == "onycholysis"
    assert finding["display_name"] == "Nail separation (onycholysis)"
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["track_used"] == "color"
    assert finding["failure_reason"] == failure_reason
