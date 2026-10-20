from ml.infer import validation_policy as vp


def _f(label, verdict="outside"):
    return {"label": label, "verdict": verdict, "confidence": 0.7}


def test_limited_signs_are_tagged_not_blocked():
    out = vp.apply([_f("beaus_lines")], metadata={})
    assert all(f["validation_tier"] == "limited" and f["verdict"] == "outside" for f in out)


def test_validated_and_withheld_signs_have_no_limited_tag():
    out = vp.apply([_f("pitting"), _f("terrys_nails"), _f("muehrckes_lines")], metadata={})
    assert "validation_tier" not in out[0] and out[0]["verdict"] == "outside"
    assert out[1]["verdict"] == "inconclusive" and out[1]["failure_reason"] == "not_validated"


def test_inconclusive_limited_sign_is_not_tagged():
    out = vp.apply([_f("beaus_lines", "inconclusive")], metadata={})
    assert "validation_tier" not in out[0]
