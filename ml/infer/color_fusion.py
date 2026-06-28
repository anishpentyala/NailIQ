"""Fuse the classical colour heuristics with the colour-condition CNN.

Parallel to fusion.py (geometry + CNN), but with a deliberately DIFFERENT trust model,
because the two situations aren't symmetric:

  - In fusion.py the geometry track is a real measurement (an angle, a sagitta), so it
    is the authority and a disagreeing CNN only downgrades the result to inconclusive.
  - Here the "classical" track is a bundle of uncalibrated heuristics that, on real
    labeled photos, separated positive from negative only a little better than chance
    (ml/eval/calibrate_color.py). Letting that veto a CNN trained on the same labels
    would throw away the whole reason the CNN exists.

So for the colour conditions the CNN was trained on (cyanosis, terrys_nails,
beaus_lines, muehrckes_lines, pitting, and -- once the Ghana fingernail-anemia set was
folded in, see data/DATASETS_DIVERSITY.md -- pallor) the CNN is PRIMARY: when it has a
confident call, it sets the verdict; the heuristic can only corroborate it (boosting
confidence on agreement), never overturn it. When the CNN has no confident call, the
heuristic stands alone, exactly as before. Conditions the CNN doesn't cover
(leukonychia, melanonychia, lindsays_nails, onycholysis, splinter_hemorrhages) pass
through untouched. Which labels are "covered" is read from the model's own manifest
(color_classifier.app_conditions()), not hardcoded here -- see pipeline.py's call site.

The single-label CNN can name only one condition per nail, so a confident prediction of
some OTHER condition is treated as "no opinion" on C (it can't rule out a co-occurring
sign) rather than as evidence C is absent -- the screener-safe choice. The output stays
within / outside / inconclusive, never a diagnosis.
"""


def _cnn_signal_for(condition, pred):
    """Map a CNN prediction onto one condition's within/outside axis (or no opinion)."""
    if pred is None or pred.get("predicted_label") is None:
        return None, None
    label = pred["predicted_label"]
    if label == "healthy":
        return "within", pred["confidence"]
    if label == condition:
        return "outside", pred["confidence"]
    return None, None  # confident about a different condition -> can't rule C in or out


def _boost(heur_conf, cnn_conf):
    return min(0.97, round((heur_conf + cnn_conf) / 2 + 0.15, 2))


def _fuse_one(heur, pred):
    """heur: a classical colour finding for a CNN-covered condition. pred: CNN dict."""
    base = {
        "label": heur["label"],
        "display_name": heur["display_name"],
        "value": heur["value"],
        "unit": heur["unit"],
        "track_used": "color_fused",
        "color": {"verdict": heur["verdict"], "confidence": heur["confidence"]},
        "ml": None if pred is None else {
            "predicted_label": pred.get("predicted_label"),
            "confidence": pred.get("confidence"),
            "probs": pred.get("probs"),
        },
    }

    # If the region couldn't be measured, the heuristic is already inconclusive and the
    # CNN saw the same unlocatable region -- stay inconclusive.
    if heur["verdict"] == "inconclusive":
        return {**base, "verdict": "inconclusive", "confidence": 0.0,
                "agreement": "region_unavailable", "failure_reason": heur["failure_reason"]}

    cnn_verdict, cnn_conf = _cnn_signal_for(heur["label"], pred)

    if cnn_verdict is None:  # CNN has no confident opinion on this condition
        return {**base, "verdict": heur["verdict"], "confidence": heur["confidence"],
                "agreement": "color_only", "failure_reason": None}

    if cnn_verdict == heur["verdict"]:  # both agree -> reinforce
        return {**base, "verdict": cnn_verdict, "confidence": _boost(heur["confidence"], cnn_conf),
                "agreement": "agree", "failure_reason": None}

    # Disagree: the CNN leads (the heuristic is near-chance and cannot veto it).
    return {**base, "verdict": cnn_verdict, "confidence": cnn_conf,
            "agreement": "ml_primary", "failure_reason": None}


def fuse(color_findings, pred, covered_conditions):
    """Return colour findings with the CNN-covered ones fused; others pass through.

    color_findings: classical findings in their pipeline order.
    pred: color_classifier.predict_from_region(...) dict, or None.
    covered_conditions: the condition labels the CNN can speak to (its app_conditions).
    """
    covered = set(covered_conditions)
    out = []
    for heur in color_findings:
        out.append(_fuse_one(heur, pred) if heur["label"] in covered else heur)
    return out
