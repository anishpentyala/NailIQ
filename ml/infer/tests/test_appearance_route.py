from ml.infer import appearance, color_classifier

META = {"appearance_conditions": ["koilonychia"], "appearance_rules": {"koilonychia": {"floor": 0.1}},
        "validated_appearance_conditions": ["koilonychia"], "validated_roi_modes": ["legacy"]}


def _findings():
    geo = {"verdict": "inconclusive", "failure_reason": "measurement_unstable", "value": None}
    return [{"label": "koilonychia", "display_name": "Spoon nails", **geo, "confidence": 0.0},
            {"label": "clubbing", "display_name": "Clubbing", **geo, "confidence": 0.0}]


def test_koilonychia_answers_from_appearance_when_geometry_fails(monkeypatch):
    monkeypatch.setattr(color_classifier, "model_metadata", lambda: META)
    out = {f["label"]: f for f in appearance.fallback(_findings(), {"probs": {"koilonychia": 0.3, "healthy": 0.2}}, "legacy")}
    assert out["koilonychia"]["verdict"] == "outside" and out["koilonychia"]["track_used"] == "appearance"
    assert out["clubbing"]["verdict"] == "inconclusive"  # not enabled


def test_healthy_probability_gives_within_and_unvalidated_mode_stays_withheld(monkeypatch):
    monkeypatch.setattr(color_classifier, "model_metadata", lambda: META)
    within = appearance.fallback(_findings(), {"probs": {"koilonychia": 0.02, "healthy": 0.8}}, "legacy")[0]
    assert within["verdict"] == "within"
    withheld = appearance.fallback(_findings(), {"probs": {"koilonychia": 0.3, "healthy": 0.2}}, "assisted")[0]
    assert withheld["verdict"] == "inconclusive" and withheld["failure_reason"] == "not_validated"
