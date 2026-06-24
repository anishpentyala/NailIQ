import numpy as np

from ml.infer.cyanosis import (
    build_finding,
    inconclusive_finding,
    measure,
    to_verdict,
    CYANOSIS_RAW_B_MAX,
)


def _region(nail_raw_lab_b=None, lab_b=None):
    """Minimal synthetic region dict for cyanosis testing.

    nail_raw_lab_b: the raw (pre-white-balance) nail b* the detector reads.
    lab_b: white-balanced nail b* array, used only to exercise the fallback path
           when nail_raw_lab_b is absent (older region dicts).
    """
    region = {
        "S": np.full(100, 0.5),
        "V": np.full(100, 0.6),
    }
    if nail_raw_lab_b is not None:
        region["nail_raw_lab_b"] = float(nail_raw_lab_b)
    if lab_b is not None:
        region["lab_b"] = np.asarray(lab_b, dtype=np.float64)
    return region


def test_cyanosis_normal_yellowish_nail_is_within():
    """A normal nail with a clearly yellow raw b* (well above the cutoff) -> within."""
    region = _region(nail_raw_lab_b=12.0)
    assert measure(region) == 12.0
    assert to_verdict(12.0) == "within"
    assert build_finding(region)["verdict"] == "within"


def test_cyanosis_bluish_nail_is_outside():
    """A distinctly blue nail (negative raw b*) -> outside."""
    region = _region(nail_raw_lab_b=-8.0)
    assert measure(region) == -8.0
    assert to_verdict(-8.0) == "outside"
    assert build_finding(region)["verdict"] == "outside"


def test_cyanosis_threshold_is_inclusive_within():
    """Raw b* exactly at the cutoff -> within (only strictly bluer flags), limiting
    false positives."""
    region = _region(nail_raw_lab_b=CYANOSIS_RAW_B_MAX)
    assert to_verdict(measure(region)) == "within"


def test_cyanosis_just_below_threshold_is_outside():
    """Raw b* just under the cutoff -> outside."""
    region = _region(nail_raw_lab_b=CYANOSIS_RAW_B_MAX - 1.0)
    assert to_verdict(measure(region)) == "outside"


def test_cyanosis_falls_back_to_white_balanced_b_when_raw_absent():
    """An older region dict without nail_raw_lab_b uses the white-balanced b* median."""
    region = _region(lab_b=np.full(100, -7.0))
    assert measure(region) == -7.0
    assert build_finding(region)["verdict"] == "outside"


def test_cyanosis_inconclusive_finding():
    """inconclusive_finding returns the right structure."""
    finding = inconclusive_finding("nail_region_unclear")
    assert finding["label"] == "cyanosis"
    assert finding["verdict"] == "inconclusive"
    assert finding["confidence"] == 0.0
    assert finding["failure_reason"] == "nail_region_unclear"
    assert finding["track_used"] == "color"
