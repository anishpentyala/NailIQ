import numpy as np
import pytest

from ml.infer import specialists as spec

IMG = np.full((100, 100, 3), 120, np.uint8)
BOX = [0.2, 0.2, 0.8, 0.8]


def _findings():
    return [
        {"label": "onycholysis", "display_name": "Nail separation (onycholysis)", "verdict": "inconclusive", "confidence": 0.0},
        {"label": "leukonychia", "display_name": "White nails (leukonychia)", "verdict": "within", "confidence": 0.4},
        {"label": "melanonychia", "display_name": "Dark nail band (melanonychia)", "verdict": "within", "confidence": 0.4},
        {"label": "pitting", "verdict": "within"},
    ]


def _patch(monkeypatch, probs, thr=0.1, available=("onycholysis", "leukonychia", "melanonychia")):
    monkeypatch.setattr(spec, "is_available", lambda s: s in available and s in spec.ENABLED)
    monkeypatch.setattr(spec, "threshold", lambda s: thr)
    monkeypatch.setattr(spec, "probability", lambda s, nail: probs[s])


def test_enabled_allowlist():
    assert set(spec.ENABLED) == {"onycholysis", "leukonychia"}


def test_outside_and_within_per_sign(monkeypatch):
    _patch(monkeypatch, {"onycholysis": 0.6, "leukonychia": 0.01, "melanonychia": 0.99})
    out = {f["label"]: f for f in spec.apply(_findings(), IMG, BOX)}
    assert out["onycholysis"]["verdict"] == "outside" and out["onycholysis"]["ml"]["predicted_label"] == "onycholysis"
    assert out["onycholysis"]["track_used"] == "color_fused" and out["onycholysis"]["value"] is None
    assert 0.5 <= out["onycholysis"]["confidence"] <= 0.9
    assert out["leukonychia"]["verdict"] == "within" and out["leukonychia"]["display_name"] == "White nails (leukonychia)"
    # melanonychia is withheld (not in ENABLED): its classical finding passes through untouched
    assert out["melanonychia"]["verdict"] == "within" and out["melanonychia"].get("track_used") != "color_fused"
    assert out["pitting"] == {"label": "pitting", "verdict": "within"}


@pytest.mark.parametrize("available,box", [((), BOX), (("onycholysis", "leukonychia"), None)])
def test_unavailable_or_no_box_leaves_findings(monkeypatch, available, box):
    _patch(monkeypatch, {"onycholysis": 0.9, "leukonychia": 0.9, "melanonychia": 0.9}, available=available)
    assert spec.apply(_findings(), IMG, box) == _findings()
