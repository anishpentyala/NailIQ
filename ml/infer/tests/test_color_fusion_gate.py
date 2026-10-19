from ml.infer import color_fusion as cf


def _heur(label, verdict="outside"):
    return {"label": label, "display_name": label, "value": None, "unit": None, "verdict": verdict,
            "confidence": 0.5, "failure_reason": None}


def _pred(label, p_label, p_healthy):
    return {"predicted_label": label, "confidence": max(p_label, p_healthy),
            "probs": {label: p_label, "healthy": p_healthy}}


def test_healthy_signal_withholds_splinter_outside():
    f = cf._fuse_one(_heur("splinter_hemorrhages"), _pred("splinter_hemorrhages", 0.6, 0.15))
    assert f["verdict"] == "inconclusive" and f["agreement"] == "healthy_signal"


def test_low_healthy_probability_keeps_the_flag():
    f = cf._fuse_one(_heur("splinter_hemorrhages"), _pred("splinter_hemorrhages", 0.8, 0.03))
    assert f["verdict"] == "outside"


def test_gate_ignores_conditions_not_in_table():
    f = cf._fuse_one(_heur("cyanosis"), _pred("cyanosis", 0.6, 0.3))
    assert f["verdict"] == "outside"
