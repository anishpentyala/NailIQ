"""Tuned color decision rules (color_fusion OVR / heuristic-support tables) and the
validation policy. Synthetic dicts only."""
from ml.infer import color_classifier, color_fusion, onychogryphosis, validation_policy


def _heur(label, verdict):
    return {"label": label, "display_name": label, "value": None, "unit": None,
            "verdict": verdict, "confidence": 0.5, "track_used": "color", "failure_reason": None}


def _opinion(**probs):
    full = {"healthy": 0.0, **probs}
    return color_classifier.opinion_from_probs(full)


def test_opinion_respects_top_class_floor():
    assert _opinion(healthy=0.9, pitting=0.1)["predicted_label"] == "healthy"
    assert _opinion(healthy=0.3, pitting=0.25, pallor=0.2)["predicted_label"] is None


def test_ovr_votes_outside_when_condition_is_a_close_second(monkeypatch):
    monkeypatch.setitem(color_fusion.OVR_THRESHOLD, "beaus_lines", 0.15)
    pred = _opinion(muehrckes_lines=0.7, beaus_lines=0.2)
    out = color_fusion._fuse_one(_heur("beaus_lines", "within"), pred)
    assert out["verdict"] == "outside"


def test_ovr_below_cutoff_keeps_old_behaviour(monkeypatch):
    monkeypatch.setitem(color_fusion.OVR_THRESHOLD, "beaus_lines", 0.15)
    pred = _opinion(muehrckes_lines=0.9, beaus_lines=0.05)
    out = color_fusion._fuse_one(_heur("beaus_lines", "within"), pred)
    assert out["verdict"] == "within" and out["agreement"] == "color_only"


def test_uncorroborated_heuristic_outside_becomes_inconclusive(monkeypatch):
    """The measured failure: CNN confidently says pallor on a healthy nail, fusion had
    no opinion on pitting, and the near-chance pitting heuristic fired."""
    monkeypatch.setitem(color_fusion.HEURISTIC_MIN_CNN_SUPPORT, "pitting", 0.05)
    monkeypatch.delitem(color_fusion.OVR_THRESHOLD, "pitting", raising=False)
    pred = _opinion(pallor=0.9, pitting=0.01)
    out = color_fusion._fuse_one(_heur("pitting", "outside"), pred)
    assert out["verdict"] == "inconclusive"
    assert out["failure_reason"] == "heuristic_uncorroborated"


def test_corroborated_heuristic_outside_stands(monkeypatch):
    monkeypatch.setitem(color_fusion.HEURISTIC_MIN_CNN_SUPPORT, "pitting", 0.05)
    monkeypatch.delitem(color_fusion.OVR_THRESHOLD, "pitting", raising=False)
    pred = _opinion(pallor=0.85, pitting=0.1)
    assert color_fusion._fuse_one(_heur("pitting", "outside"), pred)["verdict"] == "outside"


def test_support_rule_never_touches_within(monkeypatch):
    monkeypatch.setitem(color_fusion.HEURISTIC_MIN_CNN_SUPPORT, "pitting", 0.05)
    pred = _opinion(pallor=0.9, pitting=0.0)
    assert color_fusion._fuse_one(_heur("pitting", "within"), pred)["verdict"] == "within"


def test_policy_withholds_unvalidated_verdicts_but_keeps_them_for_feedback():
    findings = [_heur("pallor", "outside"), _heur("cyanosis", "outside"), _heur("leukonychia", "inconclusive")]
    out = validation_policy.apply(findings)
    assert out[0]["verdict"] == "inconclusive"
    assert out[0]["failure_reason"] == "not_validated"
    assert out[0]["unvalidated_verdict"] == "outside"
    assert out[1]["verdict"] == "outside"
    assert "unvalidated_verdict" not in out[2]


def _placeholder():
    return onychogryphosis.build_finding(region=None)


def test_cnn_only_condition_follows_confident_cnn_call():
    out = color_fusion._fuse_one(_placeholder(), _opinion(onychogryphosis=0.9, healthy=0.1))
    assert out["verdict"] == "outside" and out["agreement"] == "ml_only"
    out = color_fusion._fuse_one(_placeholder(), _opinion(healthy=0.9))
    assert out["verdict"] == "within"


def test_cnn_only_condition_is_inconclusive_without_a_confident_call():
    out = color_fusion._fuse_one(_placeholder(), _opinion(healthy=0.3, pitting=0.25, pallor=0.2))
    assert out["verdict"] == "inconclusive" and out["failure_reason"] == "no_confident_ai_call"
    out = color_fusion._fuse_one(_placeholder(), None)
    assert out["verdict"] == "inconclusive"


def test_cnn_only_placeholder_never_claims_within_on_its_own():
    assert _placeholder()["verdict"] == "inconclusive"
