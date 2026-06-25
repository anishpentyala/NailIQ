"""color_fusion: CNN-primary fusion of the classical colour heuristics with the CNN.

Synthetic finding/prediction dicts only -- no model, no images. Verifies the trust
model documented in color_fusion.py: the CNN leads on its covered conditions, the
heuristic only corroborates, uncovered conditions pass through untouched.
"""

from ml.infer import color_fusion

COVERED = ["cyanosis", "terrys_nails", "beaus_lines", "muehrckes_lines", "pitting"]


def _heur(label, verdict, confidence=0.5):
    return {
        "label": label, "display_name": f"Nail ({label})", "value": None, "unit": None,
        "verdict": verdict, "confidence": confidence, "track_used": "color",
        "failure_reason": None if verdict != "inconclusive" else "nail_region_unclear",
    }


def _pred(predicted_label, confidence=0.8):
    return {"predicted_label": predicted_label, "confidence": confidence,
            "probs": {predicted_label or "healthy": confidence}}


def test_uncovered_condition_passes_through_unchanged():
    heur = _heur("leukonychia", "outside")
    out = color_fusion.fuse([heur], _pred("cyanosis"), COVERED)
    assert out[0] is heur  # identical object, untouched


def test_cnn_no_opinion_keeps_heuristic():
    """Low-confidence CNN (predicted_label None) -> heuristic stands, color_only."""
    heur = _heur("pitting", "within", 0.4)
    out = color_fusion.fuse([heur], _pred(None, 0.3), COVERED)[0]
    assert out["verdict"] == "within"
    assert out["confidence"] == 0.4
    assert out["agreement"] == "color_only"
    assert out["track_used"] == "color_fused"


def test_cnn_other_condition_is_no_opinion():
    """CNN confidently names a DIFFERENT condition -> no opinion on this one."""
    heur = _heur("cyanosis", "within")
    out = color_fusion.fuse([heur], _pred("terrys_nails"), COVERED)[0]
    assert out["verdict"] == "within"
    assert out["agreement"] == "color_only"


def test_agreement_boosts_confidence():
    heur = _heur("terrys_nails", "outside", 0.5)
    out = color_fusion.fuse([heur], _pred("terrys_nails", 0.8), COVERED)[0]
    assert out["verdict"] == "outside"
    assert out["agreement"] == "agree"
    assert out["confidence"] > 0.5  # boosted above the heuristic's own confidence


def test_cnn_overrides_heuristic_false_positive():
    """CNN says healthy, heuristic flagged outside -> CNN leads (ml_primary), within."""
    heur = _heur("beaus_lines", "outside", 0.5)
    out = color_fusion.fuse([heur], _pred("healthy", 0.9), COVERED)[0]
    assert out["verdict"] == "within"
    assert out["agreement"] == "ml_primary"
    assert out["confidence"] == 0.9


def test_cnn_catches_sign_heuristic_missed():
    """CNN says the condition is present, heuristic said within -> CNN leads, outside."""
    heur = _heur("pitting", "within", 0.5)
    out = color_fusion.fuse([heur], _pred("pitting", 0.85), COVERED)[0]
    assert out["verdict"] == "outside"
    assert out["agreement"] == "ml_primary"


def test_inconclusive_region_stays_inconclusive():
    heur = _heur("cyanosis", "inconclusive")
    out = color_fusion.fuse([heur], _pred("cyanosis"), COVERED)[0]
    assert out["verdict"] == "inconclusive"
    assert out["agreement"] == "region_unavailable"
    assert out["failure_reason"] == "nail_region_unclear"


def test_none_prediction_keeps_all_heuristics():
    """pred=None (CNN unavailable/errored) -> covered conditions fall back to color_only."""
    heurs = [_heur("cyanosis", "within"), _heur("pitting", "outside")]
    out = color_fusion.fuse(heurs, None, COVERED)
    assert [o["verdict"] for o in out] == ["within", "outside"]
    assert all(o["agreement"] == "color_only" for o in out)
