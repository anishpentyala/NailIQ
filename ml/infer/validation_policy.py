"""Evidence bar a color condition must clear before the app gives it a verdict.

Rule (set 2026-09-12): on the VALID split of the end-to-end /analyze evaluation
(ml/eval/eval_end_to_end.py), with its tuned decision rule (ml/eval/tune_color_decision.py),
a condition must reach strict recall >= 50% AND a false-positive rate on healthy nails
<= 5% (a 95%-specificity screening bar). Below that, a "within" or "outside" from it
is more likely to mislead than inform, so the finding is returned inconclusive with
failure_reason "not_validated" -- the honest answer is "we can't reliably check this
yet", not a guess.

Measured status (valid -> test, strict):
  pallor               recall 55.5% FP 15.9% -> test 58.8% / 26.2%. The CNN reads many
                       darker-skin healthy nails as pallor; no cutoff separates them
                       (FP 5.3% only at recall 7.7%). A data ceiling, not a rule bug.
  leukonychia          recall 45.0% FP 0.8%  -> test 30.4% / 1.2%
  onycholysis          recall 21.1% FP 0.4%  -> test 0.0% / 7.6%
  splinter_hemorrhages recall 10.0% FP 0.8%  -> test 11.8% / 1.7%
  melanonychia         no licensed training data and no valid-split positives; its only
                       evaluable images (6, test) were all missed.
Passing on valid: cyanosis, terrys_nails, beaus_lines, muehrckes_lines, pitting,
lindsays_nails (lindsays_nails is borderline: 52.0% valid recall but 41.9% on test).

The underlying verdict is kept as `unvalidated_verdict` so /feedback responses can still
be collected against it -- that is how these conditions can earn their way back in.
Re-run the tuner after any retrain or data change and update UNVALIDATED_CONDITIONS.
"""

UNVALIDATED_CONDITIONS = {
    "pallor",
    "leukonychia",
    "onycholysis",
    "splinter_hemorrhages",
    "melanonychia",
}


def apply(findings):
    out = []
    for f in findings:
        if f["label"] in UNVALIDATED_CONDITIONS and f["verdict"] != "inconclusive":
            f = {**f, "unvalidated_verdict": f["verdict"], "verdict": "inconclusive",
                 "confidence": 0.0, "failure_reason": "not_validated"}
        out.append(f)
    return out
