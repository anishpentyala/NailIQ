from ml.infer.skin_tone import (
    apply_coverage,
    coverage_tier,
    ita_band,
    skin_tone_summary,
)


def _findings(conf=0.65):
    return [
        {"label": "leukonychia", "verdict": "within", "confidence": conf},
        {"label": "cyanosis", "verdict": "outside", "confidence": conf},
    ]


def test_band_edges():
    assert ita_band(60.0) == "very_light"
    assert ita_band(35.0) == "light"
    assert ita_band(22.0) == "intermediate"
    assert ita_band(15.0) == "tan"
    assert ita_band(0.0) == "brown"
    assert ita_band(-40.0) == "dark"
    assert ita_band(None) is None


def test_coverage_tiers():
    assert coverage_tier("very_light") == "well"
    assert coverage_tier("tan") == "limited"
    assert coverage_tier("dark") == "minimal"
    assert coverage_tier(None) == "well"  # unmeasurable tone -> don't penalize


def test_light_tone_passes_through_untouched():
    findings = apply_coverage(_findings(), skin_ita=60.0)
    assert all("tone_caveat" not in f for f in findings)
    assert all(f["confidence"] == 0.65 for f in findings)


def test_unmeasured_tone_passes_through_untouched():
    findings = apply_coverage(_findings(), skin_ita=None)
    assert all("tone_caveat" not in f for f in findings)


def test_limited_tone_caps_confidence_and_annotates():
    findings = apply_coverage(_findings(0.65), skin_ita=15.0)  # tan
    for f in findings:
        assert f["confidence"] == 0.50
        assert f["skin_tone_band"] == "tan"
        assert f["tone_tier"] == "limited"
        assert "under-represented" in f["tone_caveat"]


def test_minimal_tone_caps_harder():
    findings = apply_coverage(_findings(0.65), skin_ita=-40.0)  # dark
    assert all(f["confidence"] == 0.40 for f in findings)
    assert all(f["tone_tier"] == "minimal" for f in findings)
    assert all("darker skin tones" in f["tone_caveat"] for f in findings)


def test_cap_never_raises_confidence():
    # A finding already below the cap keeps its lower value.
    findings = apply_coverage([{"label": "x", "confidence": 0.2}], skin_ita=-40.0)
    assert findings[0]["confidence"] == 0.2


def test_summary_shape():
    s = skin_tone_summary(-40.0)
    assert s == {"ita": -40.0, "band": "dark", "coverage": "minimal"}
    assert skin_tone_summary(None) == {"ita": None, "band": None, "coverage": "well"}
