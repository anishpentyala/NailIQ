"""Pallor detection tests."""

import numpy as np
import pytest

from ..pallor import (
    PALLOR_ABS_A_MAX,
    PALLOR_REDNESS_DROP_THRESHOLD,
    build_finding,
    inconclusive_finding,
    measure,
    to_verdict,
)


def make_region(nail_a, skin_a, skin_b=0.0, skin_ita=None):
    """Helper to construct a minimal region dict with the keys pallor.py uses."""
    return {
        "lab_a": np.full(1000, nail_a, dtype=np.float64),
        "lab_b": np.full(1000, 0.0, dtype=np.float64),
        "S": np.full(1000, 0.5, dtype=np.float64),
        "V": np.full(1000, 0.7, dtype=np.float64),
        "skin_lab_a": skin_a,
        "skin_lab_b": skin_b,
        "skin_ita": skin_ita,
        "region_px": 1000,
        "finger_px": 2000,
        "across": np.zeros(1000),
        "along": np.linspace(0, 1, 1000),
        "grid_v": np.full((64, 48), 0.7),
        "grid_s": np.full((64, 48), 0.5),
        "H": np.zeros(1000),
        "glare_frac": 0.01,
        "bbox": (100, 100, 200, 200),
        "bbox_norm": (0.1, 0.1, 0.2, 0.2),
    }


class TestMeasure:
    """Test the measure function."""

    def test_normal_nail_pink_skin(self):
        """Normal pink nail with healthy redness relative to skin."""
        region = make_region(nail_a=20.0, skin_a=28.0)
        nail_a, redness_drop = measure(region)
        assert nail_a == 20.0
        assert redness_drop == 8.0

    def test_skin_lab_a_none_raises(self):
        """When skin_lab_a is None, measure raises."""
        region = make_region(nail_a=15.0, skin_a=None)
        with pytest.raises(ValueError):
            measure(region)


class TestToVerdict:
    """Test the to_verdict function."""

    def test_within_normal_redness(self):
        """Normal nail redness -> within."""
        verdict = to_verdict(nail_a=20.0, redness_drop=5.0)
        assert verdict == "within"

    def test_within_high_absolute_a(self):
        """Even with large redness_drop, high absolute nail_a -> within."""
        verdict = to_verdict(nail_a=20.0, redness_drop=12.0)
        assert verdict == "within"

    def test_outside_pale_nail(self):
        """Markedly pale nail: both redness_drop and low nail_a -> outside."""
        verdict = to_verdict(nail_a=5.0, redness_drop=10.0)
        assert verdict == "outside"

    def test_outside_boundary(self):
        """Just below absolute a threshold with sufficient redness_drop -> outside."""
        verdict = to_verdict(
            nail_a=PALLOR_ABS_A_MAX - 0.1,
            redness_drop=PALLOR_REDNESS_DROP_THRESHOLD + 0.1,
        )
        assert verdict == "outside"

    def test_within_below_redness_drop_threshold(self):
        """redness_drop below threshold, even with low nail_a -> within."""
        verdict = to_verdict(nail_a=5.0, redness_drop=7.0)
        assert verdict == "within"


class TestBuildFinding:
    """Test build_finding with realistic regions."""

    def test_normal_pink_nail(self):
        """Normal pink nail relative to skin -> within."""
        region = make_region(nail_a=20.0, skin_a=28.0)
        finding = build_finding(region)
        assert finding["label"] == "pallor"
        assert finding["display_name"] == "Nail color (pallor)"
        assert finding["verdict"] == "within"
        assert finding["value"] is None
        assert finding["unit"] is None
        assert finding["track_used"] == "color"
        assert finding["failure_reason"] is None
        assert finding["confidence"] > 0.0

    def test_markedly_pale_nail(self):
        """Pale nail: large redness_drop and low absolute nail_a -> outside."""
        region = make_region(nail_a=5.0, skin_a=25.0)
        finding = build_finding(region)
        assert finding["verdict"] == "outside"
        assert finding["confidence"] > 0.0

    def test_skin_lab_a_none(self):
        """When skin_lab_a is None, return inconclusive with nail_region_unclear."""
        region = make_region(nail_a=15.0, skin_a=None)
        finding = build_finding(region)
        assert finding["verdict"] == "inconclusive"
        assert finding["confidence"] == 0.0
        assert finding["failure_reason"] == "nail_region_unclear"
        assert finding["label"] == "pallor"
        assert finding["display_name"] == "Nail color (pallor)"


class TestInconclusiveFinding:
    """Test inconclusive_finding."""

    def test_inconclusive_shape(self):
        """inconclusive_finding returns correct shape."""
        finding = inconclusive_finding("test_failure")
        assert finding["label"] == "pallor"
        assert finding["display_name"] == "Nail color (pallor)"
        assert finding["verdict"] == "inconclusive"
        assert finding["confidence"] == 0.0
        assert finding["failure_reason"] == "test_failure"
        assert finding["track_used"] == "color"
        assert finding["value"] is None
        assert finding["unit"] is None
