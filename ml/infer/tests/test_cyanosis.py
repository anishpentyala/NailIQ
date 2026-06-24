import numpy as np

from ml.infer.cyanosis import build_finding, inconclusive_finding, measure, to_verdict


def _region(lab_b, skin_lab_b=None):
    """Create a minimal synthetic region dict for cyanosis testing.

    lab_b: array of Lab b* values for nail pixels.
    skin_lab_b: Lab b* reference for skin (or None).
    """
    lab_b = np.asarray(lab_b, dtype=np.float64)
    return {
        "lab_b": lab_b,
        "skin_lab_b": skin_lab_b,
        "S": np.full_like(lab_b, 0.5),
        "V": np.full_like(lab_b, 0.6),
    }


def test_cyanosis_normal_pink_nail_is_within():
    """A normal pink/slightly-yellow nail (b* ~ +12) should be within."""
    region = _region(lab_b=np.full(100, 12.0), skin_lab_b=10.0)
    nail_b, bluer_than_skin = measure(region)
    assert nail_b == 12.0
    assert bluer_than_skin == -2.0  # skin is slightly redder, not relevant
    assert to_verdict(nail_b, bluer_than_skin) == "within"
    assert build_finding(region)["verdict"] == "within"


def test_cyanosis_bluish_nail_bluer_than_skin_is_outside():
    """A clearly bluish nail (b* ~ -8, skin b* ~ +12) should be outside."""
    region = _region(lab_b=np.full(100, -8.0), skin_lab_b=12.0)
    nail_b, bluer_than_skin = measure(region)
    assert nail_b == -8.0
    assert bluer_than_skin == 20.0  # skin is 20 units yellower
    assert to_verdict(nail_b, bluer_than_skin) == "outside"
    assert build_finding(region)["verdict"] == "outside"


def test_cyanosis_bluish_nail_no_skin_reference():
    """A very bluish nail (b* ~ -10) even without skin reference should flag outside."""
    region = _region(lab_b=np.full(100, -10.0), skin_lab_b=None)
    nail_b, bluer_than_skin = measure(region)
    assert nail_b == -10.0
    assert bluer_than_skin == 10.0  # compared to implicit zero (white)
    assert to_verdict(nail_b, bluer_than_skin) == "outside"
    assert build_finding(region)["verdict"] == "outside"


def test_cyanosis_borderline_nail_is_within():
    """A nail at the boundary (b* exactly at threshold, minimal difference from skin)
    should be within to avoid false positives."""
    region = _region(lab_b=np.full(100, 5.0), skin_lab_b=10.0)
    nail_b, bluer_than_skin = measure(region)
    assert nail_b == 5.0
    assert bluer_than_skin == 5.0  # just under the 6.0 threshold
    assert to_verdict(nail_b, bluer_than_skin) == "within"


def test_cyanosis_inconclusive_finding():
    """inconclusive_finding returns the right structure."""
    finding = inconclusive_finding("nail_region_unclear")
    assert finding["label"] == "cyanosis"
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["failure_reason"] == "nail_region_unclear"
    assert finding["track_used"] == "color"
