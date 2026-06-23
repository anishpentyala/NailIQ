"""Fuse the geometry track and the trained-CNN track into one verdict per condition.

Showing four raw cards (geometry clubbing, geometry koilonychia, ML side, ML top)
is both cluttered and dishonest about how much they reinforce each other. This
combines them into one card per condition with a clear agreement state, while
keeping the app's hard rule intact: the output is only ever within / outside /
inconclusive, never a named diagnosis.

Which ML signal we trust: the TOP-down photo. The CNN was trained on top-down
nail images, so its top-view prediction is the meaningful one; the side-view ML
output is a domain mismatch and is deliberately not used here -- on the side
profile, geometry is the authority.

Rules per condition C (clubbing or koilonychia):
  - geometry inconclusive            -> inconclusive (geometry gates measurement)
  - ML missing / low-confidence /
    predicting the *other* condition  -> geometry alone stands (agreement: geometry_only)
  - geometry and ML agree (both
    within, or both outside on C)      -> agree, confidence boosted
  - they disagree                      -> inconclusive ("tracks_disagree"): we will
                                          not assert a verdict the two tracks split on
"""

# Map a top-view CNN prediction onto a single condition's within/outside axis.
# Predicting a *different* condition tells us nothing about this one.
def _ml_signal_for(condition, ml):
    if ml is None or ml["verdict"] == "inconclusive" or ml.get("predicted_label") is None:
        return None, None
    predicted = ml["predicted_label"]
    if predicted == "healthy":
        return "within", ml["confidence"]
    if predicted == condition:
        return "outside", ml["confidence"]
    return None, None  # ML flagged the other condition -> not informative here


def _agree_confidence(geom_conf, ml_prob):
    return min(0.97, round((geom_conf + ml_prob) / 2 + 0.15, 2))


def _fuse_one(geom, ml):
    """geom: a geometry finding (clubbing/koilonychia). ml: the top-view ML finding."""
    base = {
        "label": geom["label"],
        "display_name": geom["display_name"],
        "value": geom["value"],
        "unit": geom["unit"],
        "track_used": "fused",
        "geometry": {"verdict": geom["verdict"], "value": geom["value"],
                     "confidence": geom["confidence"]},
        "ml": None if ml is None else {
            "verdict": ml["verdict"], "predicted_label": ml.get("predicted_label"),
            "confidence": ml["confidence"],
        },
    }

    if geom["verdict"] == "inconclusive":
        return {**base, "verdict": "inconclusive", "confidence": 0.0,
                "agreement": "geometry_unavailable", "failure_reason": geom["failure_reason"]}

    ml_verdict, ml_prob = _ml_signal_for(geom["label"], ml)

    if ml_verdict is None:
        return {**base, "verdict": geom["verdict"], "confidence": geom["confidence"],
                "agreement": "geometry_only", "failure_reason": None}

    if ml_verdict == geom["verdict"]:
        return {**base, "verdict": geom["verdict"],
                "confidence": _agree_confidence(geom["confidence"], ml_prob),
                "agreement": "agree", "failure_reason": None}

    return {**base, "verdict": "inconclusive", "confidence": 0.0,
            "agreement": "disagree", "failure_reason": "tracks_disagree"}


def fuse(geometry_findings, ml_top_finding):
    """Return one fused finding per geometry finding, in the same order."""
    return [_fuse_one(geom, ml_top_finding) for geom in geometry_findings]
