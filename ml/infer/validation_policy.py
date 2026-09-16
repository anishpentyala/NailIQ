"""Evidence bar a color condition must clear before the app gives it a verdict.

Rule (set 2026-09-12): on the VALID split of the end-to-end /analyze evaluation
(ml/eval/eval_end_to_end.py), with its tuned decision rule (ml/eval/tune_color_decision.py),
a condition must reach strict recall >= 50% AND a false-positive rate on healthy nails
<= 5% (a 95%-specificity screening bar). Below that, a "within" or "outside" from it
is more likely to mislead than inform, so the finding is returned inconclusive with
failure_reason "not_validated" -- the honest answer is "we can't reliably check this
yet", not a guess.

Updated 2026-09-15 after data/raw/nail-disease was removed as a training AND eval source
(watermark audit -- see scripts/build_color_classification_dataset.py's module
docstring) and the chaa dataset backfilled splinter_hemorrhages. Measured status
(valid -> test, strict, current model):
  pallor               recall 58.9% FP 19.8% -> test 64.5% / 23.0%. The CNN reads many
                       darker-skin healthy nails as pallor; no cutoff separates them
                       (FP 5.3% only at recall 7.7%, measured pre-retrain). A data
                       ceiling, not a rule bug -- unchanged by this retrain since the
                       Ghana pallor/healthy data wasn't touched.
  leukonychia          no vetted eval source since nail-disease's removal (was its only
                       source); 0 valid/test positives. Was already unvalidated.
  onycholysis          same as leukonychia -- 0 valid/test positives, no vetted source.
                       Was already unvalidated.
  lindsays_nails       NEWLY unvalidated: nail-disease was both its only CNN training
                       source and its only eval source (KNM alone has 2 boxes, below any
                       usable threshold); with nail-disease gone the class doesn't exist
                       in the model and there are 0 eval positives either. Previously
                       borderline-passing (52.0% valid / 41.9% test) on nail-disease data
                       that a watermark audit later found was contaminated -- that number
                       should not have been trusted even before the removal.
  melanonychia         no licensed training data (arthitaya's Kaggle license is
                       "Unknown"); stays classical-heuristic-only.
Passing on valid (2026-09-15 retrain): cyanosis (58.0%/2.4%), terrys_nails (54.0%/2.6%),
beaus_lines (58.1%/2.3%), muehrckes_lines (51.7%/0.4%), pitting (84.9%/2.9%),
splinter_hemorrhages (83.8%/2.4%) -- NEWLY VALIDATED, the payoff of the chaa dataset
replacing the contaminated nail-disease source. Its test numbers (71.7% recall, 1.5% FP)
confirm this isn't a valid-split fluke. beaus_lines/muehrckes_lines/terrys_nails all have
a real valid->test recall gap (e.g. beaus_lines 58.1%->45.5%, n=22 on test) worth
watching on the next retrain -- small test-split n for these conditions means a few
examples flip the number by several points; per the tuner's own design the VALID number
gates the policy, not test, so none of them move to unvalidated over this alone, but
don't read the test numbers above as "these clearly still work" either.

The underlying verdict is kept as `unvalidated_verdict` so /feedback responses can still
be collected against it -- that is how these conditions can earn their way back in.
Re-run the tuner after any retrain or data change and update UNVALIDATED_CONDITIONS.
"""

UNVALIDATED_CONDITIONS = {
    "pallor",
    "leukonychia",
    "onycholysis",
    "lindsays_nails",
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
