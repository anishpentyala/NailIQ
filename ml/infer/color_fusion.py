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
scripts/build_color_classification_dataset.py's module docstring.

leukonychia, onycholysis, and lindsays_nails joined/rejoined this set 2026-09-16: the
NIHATI dataset (see scripts/build_color_classification_dataset.py's add_nihati)
restored all three as CNN classes after nail-disease's removal took them away, but its
eval-positive counts are minuscule (n=4-6 on the VALID split, ml/eval/e2e_valid.json) --
an order of magnitude smaller than splinter_hemorrhages' old n=18 threshold for this
same exception. onycholysis in particular measured 0% end-to-end recall (0/4) on this
retrain. None of the three have enough held-out evidence yet to let the CNN unilaterally
overrule the heuristic; re-evaluate for removal only once a retrain grows their test-set
n meaningfully (see ml/infer/validation_policy.py for the parallel caveat on trusting
their verdicts at all).
"""

LOW_SAMPLE_CONDITIONS = {"onycholysis", "leukonychia", "lindsays_nails"}

# Conditions with no classical measurement at all (see ml/infer/onychogryphosis.py):
# the CNN's confident call is the whole verdict, and with no confident call the answer
# is inconclusive rather than the placeholder heuristic's.
CNN_ONLY_CONDITIONS = {"onychogryphosis"}

# The two tables below are chosen by ml/eval/tune_color_decision.py on the VALID split
# of the end-to-end /analyze eval (ml/eval/eval_end_to_end.py) and scored once on TEST;
# re-run it after any retrain. An absent condition keeps the original behaviour.
#
# OVR_THRESHOLD: p(C) at which the CNN votes "outside" on C even when C isn't its top
# class. The pale/white-band conditions are routinely a close second to a neighbouring
# class, so top-class-only voting threw real positives away.
OVR_THRESHOLD = {
    "cyanosis": 0.15,       # 2026-10-18 FP reduction (with support 0.1): valid 56.9%/2.5% -> 53.8%/0.6%; was 0.3
    "terrys_nails": 0.3,    # 2026-09-16 retrain: was 0.4
    "beaus_lines": 0.15,
    "muehrckes_lines": 0.15,
    "pitting": 0.15,
    "splinter_hemorrhages": 0.4,  # 2026-10-18 FP reduction: valid 71.4%/2.8% -> 65.3%/1.6%; was 0.3
    "lindsays_nails": 0.15,       # NEW 2026-09-16 retrain -- class restored via NIHATI
    # 2026-09-23, CNN-only: strict valid 53.8% -> 72.3% (FP 0.0%), test 50.0% -> 67.6% (FP 0.0%)
    "onychogryphosis": 0.15,
}

# HEURISTIC_MIN_CNN_SUPPORT: a heuristic-only "outside" on C (CNN has no opinion on C)
# stands only if the CNN gives C at least this probability; otherwise inconclusive.
# Measured 2026-09-12 on valid: 100% of pitting/cyanosis/leukonychia/splinter false
# positives on healthy nails were heuristic-only, mostly on darker-skin healthy nails
# the CNN read as "pallor" -- which fusion treated as no opinion, handing those
# conditions to a near-chance heuristic.
HEURISTIC_MIN_CNN_SUPPORT = {
    "cyanosis": 0.1,        # 2026-10-18 FP reduction: was 0.02
    "beaus_lines": 0.02,
    "pitting": 0.02,
    "pallor": 0.05,         # 2026-09-16 retrain: was 0.20
    "muehrckes_lines": 0.2,
    "terrys_nails": 0.2,
    "splinter_hemorrhages": 0.2,
    "leukonychia": 0.2,     # NEW 2026-09-16 retrain -- class restored via NIHATI
    "onycholysis": 0.2,     # NEW 2026-09-16 retrain -- class restored via NIHATI
}
# Resulting strict end-to-end numbers as of the 2026-09-16 NIHATI/anemia retrain
# (scripts/build_color_classification_dataset.py's add_nihati/add_anemia) -- VALID chose
# these tables (parity-confirmed: shipped == tuner's own pick, 0 mismatches); TEST was
# never used for selection, reported here for honesty. valid -> test:
#   cyanosis             56.9%/2.6%  -> 67.7%/2.5%   (n_pos 65 -> 31)
#   terrys_nails         50.0%/2.6%  -> 44.7%/3.0%   (n_pos 148 -> 85; test recall dips
#                        below the 50% policy bar, but the policy gates on VALID only --
#                        this is the same valid->test gap documented in 2026-09-15, watch
#                        on the next retrain)
#   beaus_lines          55.3%/0.3%  -> 50.0%/0.4%   (n_pos 47 -> 28)
#   muehrckes_lines      58.3%/0.3%  -> 38.9%/0.4%   (n_pos 36 -> 18; same valid->test
#                        gap pattern as terrys_nails, smallest positive pool here)
#   pitting              60.7%/1.0%  -> 71.9%/1.7%   (n_pos 61 -> 32)
#   pallor               57.9%/15.7% -> 55.9%/21.9%  (n_pos 356 -> 365) -- fails the
#                        FP<=5% policy bar on both splits, stays unvalidated
#   leukonychia          40.0%/1.6%  -> 25.0%/1.3%   (n_pos 5 -> 4) -- fails on both;
#                        the LOW_SAMPLE_CONDITIONS fix (see above) is what makes this an
#                        honest 40%/25% instead of an inflated 80%/100% that ignored how
#                        few examples back it
#   onycholysis          0.0%/0.0%   -> 0.0%/0.4%    (n_pos 5 -> 8) -- 0% recall on both
#                        splits; the CNN is not yet catching real onycholysis positives
#   splinter_hemorrhages 71.4%/3.0%  -> 73.6%/2.1%   (n_pos 49 -> 53) -- validated on both
#   lindsays_nails       0.0%/0.0%   -> 0.0%/0.0%    (n_pos 6 -> 5) -- 0% recall on both,
#                        same LOW_SAMPLE_CONDITIONS honesty fix as leukonychia
# These are all measured through the real /analyze pipeline (region detection + bbox
# crop + fusion), not the isolated CNN -- see ml/eval/eval_color_sensitivity.py's module
# docstring for why that gap matters.


_DEFAULT_OVR = dict(OVR_THRESHOLD)
_DEFAULT_SUPPORT = dict(HEURISTIC_MIN_CNN_SUPPORT)


# HEALTHY_MAX: a specific-sign "outside" on C is withheld (inconclusive) when the CNN still gives `healthy`
# at least this probability. Idea from the "healthy vs specific disease" asymmetry in Oehler's Han-replication
# README: networks separate healthy from diseased far better than they name the disease. Picked on the
# cached VALID probabilities (tau 0.1), scored on TEST (ml/eval/e2e_*_shapes.json), without it -> with it:
#   splinter_hemorrhages valid 71%/2.8% -> 67%/1.3%, test 74%/2.1% -> 72%/0.4%
#   pitting              valid 61%/0.9% -> 59%/0.0%, test 72%/1.7% -> 69%/0.4%
# Cyanosis was tried and rejected (valid recall 57% -> 42%). Applied in _fuse_one and fuse_roi.
HEALTHY_MAX = {"splinter_hemorrhages": 0.1, "pitting": 0.1}


def _healthy_gate(finding, pred):
    cap = HEALTHY_MAX.get(finding["label"])
    if cap is None or finding.get("verdict") != "outside" or not pred:
        return finding
    if (pred.get("probs") or {}).get("healthy", 0.0) >= cap:
        return {**finding, "verdict": "inconclusive", "confidence": 0.0,
                "agreement": "healthy_signal", "failure_reason": "no_confident_ai_call"}
    return finding


def _cnn_signal_for(condition, pred, rules=None):
    """Map a CNN prediction onto one condition's within/outside axis (or no opinion)."""
    if pred is None:
        return None, None
    ovr = (OVR_THRESHOLD if rules is None else rules['ovr']).get(condition)
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


def _fuse_one(heur, pred, rules=None):
    return _healthy_gate(_fuse_one_raw(heur, pred, rules), pred)


def _fuse_one_raw(heur, pred, rules=None):
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

    if heur["label"] in CNN_ONLY_CONDITIONS:
        cnn_verdict, cnn_conf = _cnn_signal_for(heur["label"], pred, rules)
        if cnn_verdict is None:
            return {**base, "verdict": "inconclusive", "confidence": 0.0,
                    "agreement": "ml_no_opinion", "failure_reason": "no_confident_ai_call"}
        return {**base, "verdict": cnn_verdict, "confidence": cnn_conf,
                "agreement": "ml_only", "failure_reason": None}

    # If the region couldn't be measured, the heuristic is already inconclusive and the
    # CNN saw the same unlocatable region -- stay inconclusive.
    if heur["verdict"] == "inconclusive":
        return {**base, "verdict": "inconclusive", "confidence": 0.0,
                "agreement": "region_unavailable", "failure_reason": heur["failure_reason"]}

    cnn_verdict, cnn_conf = _cnn_signal_for(heur["label"], pred, rules)

    if cnn_verdict is None:  # CNN has no confident opinion on this condition
        support = (HEURISTIC_MIN_CNN_SUPPORT if rules is None else rules['support']).get(heur["label"])
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


def fuse_roi(findings, pred, covered_conditions, rules=None):
    """A located nail can support AI without a silhouette-based measurement.

    Low-sample disagreement/measurement safeguards still apply. No measurement
    is invented from the bounding rectangle.
    """
    covered = set(covered_conditions)
    out = []
    for finding in findings:
        condition = finding['label']
        if condition not in covered:
            out.append(finding)
            continue
        base = {**finding, 'track_used': 'color_fused', 'ml': pred,
                'color': {'verdict': 'inconclusive', 'confidence': 0}, 'agreement': 'ml_no_opinion',
                'roi_only': True}
        if condition in LOW_SAMPLE_CONDITIONS:
            out.append({**base, 'failure_reason': 'insufficient_data_for_confident_call'})
            continue
        verdict, confidence = _cnn_signal_for(condition, pred, rules)
        if verdict is None:
            out.append({**base, 'failure_reason': 'no_confident_ai_call'})
            continue
        out.append(_healthy_gate({**base, 'verdict': verdict, 'confidence': confidence,
            'value': None, 'unit': None, 'track_used': 'color_fused',
            'agreement': 'ml_only', 'failure_reason': None,
            'evidence_type': 'appearance', 'color': {'verdict': 'inconclusive', 'confidence': 0},
            'ml': pred}, pred))
    return out
