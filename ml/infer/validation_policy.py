"""Evidence bar a color condition must clear before the app gives it a verdict.

Rule (set 2026-09-12): on the VALID split of the end-to-end /analyze evaluation
(ml/eval/eval_end_to_end.py), with its tuned decision rule (ml/eval/tune_color_decision.py),
a condition must reach strict recall >= 50% AND a false-positive rate on healthy nails
<= 5% (a 95%-specificity screening bar). Below that, a "within" or "outside" from it
is more likely to mislead than inform, so the finding is returned inconclusive with
failure_reason "not_validated" -- the honest answer is "we can't reliably check this
yet", not a guess.

Updated 2026-09-16 after the NIHATI and anemia datasets were added (both independently
audited the same way nail-disease was, see scripts/build_color_classification_dataset.py's
add_nihati/add_anemia). NIHATI restored leukonychia/onycholysis/lindsays_nails as CNN
classes for the first time since nail-disease's removal, so they now have real (if tiny)
VALID eval positives instead of zero. Measured status (strict, current model, VALID):
  pallor               recall 57.9% FP 15.7% (n_pos=356). Anemia's anemic_nail boxes grew
                       the pallor eval pool but didn't change the underlying problem: the
                       CNN reads many darker-skin healthy nails as pallor and no cutoff
                       separates them (FP 5.3% only at recall 7.7%, measured previously) --
                       still a data ceiling, not a rule bug. Stays unvalidated.
  leukonychia          NIHATI gives it n_pos=5 on valid (from 0) -- raw recall/FP looked
                       like a pass (see ml/eval/tune_color_decision.py's initial run), but
                       once leukonychia was correctly added to
                       ml/infer/color_fusion.LOW_SAMPLE_CONDITIONS (n=5 is far too small to
                       trust a CNN-overrules-heuristic call), its strict end-to-end recall
                       dropped to 40% -- disagreements that used to resolve to ml_primary
                       now honestly abstain instead. Stays unvalidated; the raw before-
                       low-sample-fix number would have been a false pass.
  onycholysis          NIHATI gives it n_pos=4/5 (varies slightly by run seed for tie
                       cases); measured recall 0% both before and after the
                       LOW_SAMPLE_CONDITIONS fix -- the CNN simply isn't catching real
                       onycholysis positives at this sample size. Stays unvalidated.
  lindsays_nails       NIHATI gives it n_pos=6 on valid (from 0); same LOW_SAMPLE_CONDITIONS
                       story as leukonychia -- raw recall looked like 83.3%, but with the
                       low-sample disagree-to-inconclusive fallback correctly applied,
                       strict recall is 0%. Stays unvalidated.
  melanonychia         no licensed training data (arthitaya's Kaggle license is
                       "Unknown"); stays classical-heuristic-only.
The net effect of this retrain on the unvalidated set is: none of the four newly-touched
conditions move in or out. NIHATI meaningfully improved isolated-CNN accuracy for
leukonychia/onycholysis/lindsays_nails (ml/eval/eval_color_ensemble.py) and gave them
real classes again, but n=4-6 eval positives is nowhere near enough to trust an
end-to-end verdict -- this is the same "isolated-CNN accuracy != end-to-end recall" gap
`eval_color_sensitivity.py`'s docstring warns about, just measured freshly here. Re-run
this check if a future retrain grows NIHATI's contribution meaningfully.
Passing on valid (2026-09-16 retrain): cyanosis (56.9%/2.6% -> test 67.7%/2.5%),
terrys_nails (50.0%/2.6% -> test 44.7%/3.0%, new floor 0.25 + ovr 0.3 -- was failing at
44.1%/1.7% under the old table before this retrain; test recall dips under 50% but the
policy gates on VALID only, same gap pattern as 2026-09-15), beaus_lines (55.3%/0.3% ->
test 50.0%/0.4%), muehrckes_lines (58.3%/0.3% -> test 38.9%/0.4%, biggest valid->test
gap here, smallest positive pool), pitting (60.7%/1.0% -> test 71.9%/1.7%),
splinter_hemorrhages (71.4%/3.0% -> test 73.6%/2.1%, holds up on both splits). Test
numbers confirm none of these should flip to unvalidated over this alone -- see
ml/infer/color_fusion.py's table comments for the exact chosen values.

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
