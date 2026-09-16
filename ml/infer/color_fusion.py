"""Fuse the classical colour heuristics with the colour-condition CNN.

Parallel to fusion.py (geometry + CNN), but with a deliberately DIFFERENT trust model,
because the two situations aren't symmetric:

  - In fusion.py the geometry track is a real measurement (an angle, a sagitta), so it
    is the authority and a disagreeing CNN only downgrades the result to inconclusive.
  - Here the "classical" track is a bundle of uncalibrated heuristics that, on real
    labeled photos, separated positive from negative only a little better than chance
    (ml/eval/calibrate_color.py). Letting that veto a CNN trained on the same labels
    would throw away the whole reason the CNN exists.

So for the colour conditions the CNN was trained on the CNN is PRIMARY: when it has a
confident call, it sets the verdict; the heuristic can only corroborate it (boosting
confidence on agreement), never overturn it. When the CNN has no confident call, the
heuristic stands alone, exactly as before. The covered set grew as training data was
added: cyanosis, terrys_nails, beaus_lines, muehrckes_lines, pitting (KNM); pallor
(Ghana fingernail-anemia set, see data/DATASETS_DIVERSITY.md); leukonychia,
onycholysis, splinter_hemorrhages, lindsays_nails (nail-disease set) -- added because
as pure heuristics they false-positived badly on healthy nails (leukonychia ~61%), and
CNN-primary fusion is what fixed that. melanonychia was briefly added the same way via
data/raw/nail-dataset-arthitaya, then REMOVED: that dataset's Kaggle license is
"Unknown" (data/raw/LICENSES.md), an unresolved legal blocker for any model whose
weights might be shared, so scripts/build_color_classification_dataset.py no longer
trains on it. melanonychia is therefore CNN-uncovered and stands on the classical
heuristic alone -- not every app colour condition has CNN coverage, and that gap is
deliberate, not an oversight. Which labels are "covered" is read from the model's own
manifest (color_classifier.app_conditions()), not hardcoded here -- see pipeline.py's
call site.

The single-label CNN can name only one condition per nail, so a confident prediction of
some OTHER condition is treated as "no opinion" on C (it can't rule out a co-occurring
sign) rather than as evidence C is absent -- the screener-safe choice. The output stays
within / outside / inconclusive, never a diagnosis.

LOW_SAMPLE_CONDITIONS is a deliberate exception to "CNN is primary" above. onycholysis
has precision/recall numbers computed on so few images that a single test example flips
them by 5-15 points (ml/eval/eval_color_ensemble.py, ml/eval/eval_color_sensitivity.py)
-- there isn't enough evidence to say the CNN's call is more trustworthy than the
heuristic's for it specifically. Letting the CNN silently overrule the heuristic on
disagreement, as it does for the well-sampled conditions, would assert a verdict neither
signal can actually back. So for this subset, disagreement falls back to inconclusive
(`agreement: "low_sample_disagree"`) instead of `ml_primary` -- still screener-safe, and
honest about the data gap CLAUDE.md documents rather than papering over it with a
confidence float. Agreement (both signals concur) is unaffected -- that's still real
corroborating evidence regardless of sample size.

splinter_hemorrhages was in this set (test n=18) until the chaa dataset (2026-09) grew
its CNN-covered test count to n=50 with 0.98 isolated-crop recall -- see
scripts/build_color_classification_dataset.py's module docstring. onycholysis has no
CNN class at all anymore (its only source, nail-disease, was removed for the same
reason splinter_hemorrhages needed chaa in the first place -- watermark contamination),
so it stays low-sample/CNN-uncovered by construction, not by choice.
"""

LOW_SAMPLE_CONDITIONS = {"onycholysis"}

# The two tables below are chosen by ml/eval/tune_color_decision.py on the VALID split
# of the end-to-end /analyze eval (ml/eval/eval_end_to_end.py) and scored once on TEST;
# re-run it after any retrain. An absent condition keeps the original behaviour.
# leukonychia/lindsays_nails were dropped from both tables in 2026-09 (see
# color_classifier.CLASS_CONFIDENCE_THRESHOLD's comment): their only CNN source
# (nail-disease) was removed for watermark contamination and neither class exists in
# the model anymore, so an entry for either would be dead code (the CNN can never vote
# for a class it wasn't trained on).
#
# OVR_THRESHOLD: p(C) at which the CNN votes "outside" on C even when C isn't its top
# class. The pale/white-band conditions are routinely a close second to a neighbouring
# class, so top-class-only voting threw real positives away.
OVR_THRESHOLD = {
    "cyanosis": 0.15,
    "terrys_nails": 0.4,   # 2026-09 retrain: was 0.25, re-tuned alongside chaa's addition
    "beaus_lines": 0.15,
    "muehrckes_lines": 0.15,
    "pitting": 0.15,
}

# HEURISTIC_MIN_CNN_SUPPORT: a heuristic-only "outside" on C (CNN has no opinion on C)
# stands only if the CNN gives C at least this probability; otherwise inconclusive.
# Measured 2026-09-12 on valid: 100% of pitting/cyanosis/leukonychia/splinter false
# positives on healthy nails were heuristic-only, mostly on darker-skin healthy nails
# the CNN read as "pallor" -- which fusion treated as no opinion, handing those
# conditions to a near-chance heuristic.
HEURISTIC_MIN_CNN_SUPPORT = {
    "cyanosis": 0.05,       # 2026-09 retrain: was 0.02
    "beaus_lines": 0.02,
    "pitting": 0.02,        # 2026-09 retrain: was 0.05
    "pallor": 0.20,
    "muehrckes_lines": 0.2,     # NEW 2026-09 retrain
    "terrys_nails": 0.2,        # NEW 2026-09 retrain
    "splinter_hemorrhages": 0.2,  # 2026-09 retrain: was 0.02, chaa-backed re-tune
}
# Resulting strict end-to-end numbers as of the 2026-09-15 retrain (data/raw/nail-disease
# removed for watermark contamination, chaa added for splinter_hemorrhages -- see
# scripts/build_color_classification_dataset.py). VALID chose these tables; TEST was
# never used for selection, only reported here for honesty:
#   cyanosis             valid 58.0%/2.4%   test 61.5%/3.3%
#   pitting              valid 84.9%/2.9%   test 86.2%/6.2%  (test FP over the 5% policy
#                        cap despite valid being under it -- small-n test noise, watch
#                        on next retrain, see ml/infer/validation_policy.py)
#   muehrckes_lines      valid 51.7%/0.4%   test 40.0%/0.5%  (test recall below 50%; n=15
#                        on test, one of the smallest positive pools here)
#   terrys_nails         valid 54.0%/2.6%   test 50.6%/2.9%
#   beaus_lines          valid 58.1%/2.3%   test 45.5%/2.4%  (test recall below 50%; n=22)
#   splinter_hemorrhages valid 83.8%/2.4%   test 71.7%/1.5%  -- NEWLY VALIDATED (see
#                        ml/infer/validation_policy.py); previously test 11.8%/1.7% on
#                        the pre-chaa/nail-disease-sourced model.
# These are all measured through the real /analyze pipeline (region detection + bbox
# crop + fusion), not the isolated CNN -- see ml/eval/eval_color_sensitivity.py's module
# docstring for why that gap matters.


def _cnn_signal_for(condition, pred):
    """Map a CNN prediction onto one condition's within/outside axis (or no opinion)."""
    if pred is None:
        return None, None
    ovr = OVR_THRESHOLD.get(condition)
    p_condition = (pred.get("probs") or {}).get(condition, 0.0)
    if ovr is not None and p_condition >= ovr:
        return "outside", p_condition
    if pred.get("predicted_label") is None:
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
        support = HEURISTIC_MIN_CNN_SUPPORT.get(heur["label"])
        probs = (pred or {}).get("probs")
        if heur["verdict"] == "outside" and support is not None and probs \
                and probs.get(heur["label"], 0.0) < support:
            return {**base, "verdict": "inconclusive", "confidence": 0.0,
                    "agreement": "heuristic_uncorroborated", "failure_reason": "heuristic_uncorroborated"}
        return {**base, "verdict": heur["verdict"], "confidence": heur["confidence"],
                "agreement": "color_only", "failure_reason": None}

    if cnn_verdict == heur["verdict"]:  # both agree -> reinforce
        return {**base, "verdict": cnn_verdict, "confidence": _boost(heur["confidence"], cnn_conf),
                "agreement": "agree", "failure_reason": None}

    if heur["label"] in LOW_SAMPLE_CONDITIONS:
        # Neither signal has enough held-out evidence to back overruling the other here
        # (see the module docstring) -- stay inconclusive rather than assert a verdict.
        return {**base, "verdict": "inconclusive", "confidence": 0.0,
                "agreement": "low_sample_disagree", "failure_reason": "insufficient_data_for_confident_call"}

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
