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

Added 2026-09-23: onychogryphosis, a 14th condition that is CNN-only (no classical
measurement; color_fusion.CNN_ONLY_CONDITIONS). KNM-sourced eval positives. Strict, with
OVR 0.15: valid 72.3% recall / 0.0% FP (n_pos=65, n_healthy=305) -> test 67.6% / 0.0%
(n_pos=34, n_healthy=237). Passes, so it is NOT in UNVALIDATED_CONDITIONS. Caveat: it
abstains (no_confident_ai_call) on ~34-39% of healthy nails and ~26-32% of positives --
the CNN has no confident call there, and with no heuristic to fall back on the honest
answer is "couldn't analyze". Every other condition's numbers were unchanged by this.

Added 2026-10-17 (latest): melanonychia moved OUT via a specialist trained on Han positives only
(Arthitaya never trained on) plus Ghana darker-skin healthy patches as negatives (ml/infer/specialists.py,
cutoff 0.005): Arthitaya positives n=58 vs 593 healthy (Arthitaya, KNM, chaa, NIHATI, Ghana): recall 69.0% /
healthy FP 0.7% (81.0% / 2.5% at 0.002). Cutoff chosen after seeing the curve; one positive source;
recall on darker-skin melanonychia is unmeasured; Ghana healthy are small masked patches. The earlier
Han-only/no-Ghana version had 5.3% FP on Ghana healthy and stayed withheld.

Added 2026-10-17 (later): leukonychia moved OUT too, via the same specialist recipe
(ml/infer/specialists.py, cutoff 0.2): pooled leave-one-source-out 86.3% recall (n=102) / 3.6% healthy FP
(n=551); final model valid+test 90.5% / 0.8% (n=21 / 237). NIHATI held out alone: 69.0% / 3.6%.
Cutoff chosen after seeing the curves, so mildly optimistic. melanonychia has trained weights but
stays here: one positive source (Arthitaya), no darker-skin healthy nails in its evaluation.

Added 2026-10-17: onycholysis moved OUT of UNVALIDATED_CONDITIONS. It is now decided by a
dedicated fine-tuned EfficientNet-B0 (ml/infer/specialists.py, trained by
scripts/train_onycholysis_specialist.py on the app's own locator crops + the Han clinical
set), not the color CNN/heuristic. Final model, cutoff 0.3: valid 11/11 positives, 126 healthy;
test 13/13 positives, 106 healthy (cutoff chosen after seeing valid+test curves, so these are
mildly optimistic: 96% recall / 1.3% FP over 25 positives / 237 healthy). The independent evidence is
leave-one-source-out through the same front end: pooled 78.9% recall (n=95) / 4.2% healthy FP
(n=551) at the same cutoff; the margin under 5% is thin (Arthitaya's own healthy photos
fire 12-43% when that source is held out, other sources 1-4%). Tight-crop/source-photo
numbers, never measured on phone photos. See Change Log.md 2026-10-17.

The underlying verdict is kept as `unvalidated_verdict` so /feedback responses can still
be collected against it -- that is how these conditions can earn their way back in.
Re-run the tuner after any retrain or data change and update UNVALIDATED_CONDITIONS.
"""

# 2026-10-18 (false-positive reduction): melanonychia is withheld again -- the one real healthy phone
# subject scores 0.05-0.16 on its specialist (dataset healthy nails score < 0.005), so a cutoff that clears
# the phone photo would drop dataset recall to ~33%. terrys_nails is withheld too: it was the largest source
# of false alarms (3.0% of healthy nails) and a tighter rule drops VALID recall to 48.7% (<50% bar); its
# labels were also found mostly not visually Terry's (Haiku audit, 2026-10-17).
UNVALIDATED_CONDITIONS = {
    "pallor",
    "lindsays_nails",
    "melanonychia",
    "terrys_nails",
}


def apply(findings, roi_mode='legacy', metadata=None, approved=False):
    from . import color_classifier
    metadata = color_classifier.model_metadata() if metadata is None else metadata
    blocked_mode = roi_mode != 'legacy' and roi_mode not in metadata.get('validated_roi_modes', [])
    blocked_conditions = UNVALIDATED_CONDITIONS | set(metadata.get('unvalidated_conditions', []))
    out = []
    for f in findings:
        if not approved and (blocked_mode or f["label"] in blocked_conditions) and f["verdict"] != "inconclusive":
            f = {**f, "unvalidated_verdict": f["verdict"], "verdict": "inconclusive",
                 "confidence": 0.0, "failure_reason": "not_validated"}
        out.append(f)
    return out
