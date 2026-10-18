# NailIQ 60% goal — in progress

## 2026-10-02 — candidate checks finished; all-14 target UNMET

Compared six automatic experiments: MobileNet, EfficientNet and equal-weight
ensemble, each with legacy and learned-detector localization. VALID-only ranking
selected EfficientNet/legacy (9/14 signs meeting both point-estimate limits before
policy); rules and weights were frozen before TEST. Training stopped at epoch23,
with the best crop macro recall 0.802611 at epoch17 and fitted temperature0.706.
All 18,900 frozen VALID finding verdicts match offline replay, not just aggregate
counts. Canonical fingerprint comparison preserves content hashes while resolving
the relative/absolute filename difference from runpy versus module imports.

Final TEST covers 1,050 full source images, including 239 healthy-label images.
Seven signs exceed 60% strict recall; six also stay within the <=5% per-condition
healthy FP limit. Terry's nails recall76.9% has FP12/239=5.02%, so it fails without
rounding. Below60%: clubbing appearance59.6%, spoon appearance42.0%, leukonychia40.0%,
melanonychia50.0%, pallor26.1%, Lindsay0%, onycholysis0%. Policy/appearance gates
remain intact; those unsupported findings are withheld. Any pre-policy outside
finding occurs on30/239 healthy-label scans (12.6%); any shown outside on15/239
(6.3%). These rates and healthy abstentions prevent a misleading scan-level claim.

The frozen model passes all four existing healthy-phone regression modes with no
pre-policy outside finding, on one bootstrap subject only. Real phone sensitivity
and side geometry remain unvalidated. A guard audit confirms zero positive
classical Lindsay/onycholysis signals in all tested VALID crop routes; CNN-only
retraining cannot recover those same examples under the retained guard. Better
validated measurements and independent labeled evidence remain necessary.

Verification: 215 ML/backend tests pass; frontend lint/build and responsive crop
checks passed. Production weights were not replaced and no commit was created.
The assisted UI and new appearance modes remain gated. Full counts, intervals,
balanced accuracy, scan-level healthy results and all failed signs are in
`docs/goal60-results.md`; figure `docs/goal60-test-recall.png`. Frozen experiment:
`data/raw/goal60_selected_frozen_v3`. Evidence: `ml/eval/goal60_final_selection.json`,
`goal60_final_frozen_valid.json`, `goal60_final_frozen_test.json`,
`goal60_final_frozen_valid_replay.json`, `goal60_final_frozen_phone.json`.

## 2026-10-01 — approved plan implemented; candidates running

The user approved dataset-first validation, an assisted nail box, explicit use of
KNM and Arthitaya under user-reported permission, and a separately validated top-photo
appearance fallback for unreliable clubbing/spoon measurements. The target remains
strict recall >=60% for all 14 findings with healthy false-positive rate <=5%;
inconclusive results remain in every denominator. Phone accuracy and actual
geometric measurements require separate evidence.

Implemented normalized crop forwarding through capture, `/validate_photo` and
`/analyze`; touch/keyboard crop controls; optional learned nail detection; and an
appearance fallback that never fills an angle/depth measurement or overrules reliable
geometry. New ROI modes and shape findings have explicit manifest validation gates.
The crop review is advertised only after assisted-mode validation. Low-sample fusion
and the existing five withheld color conditions remain guarded. Production weights
have not been replaced.

Prepared an isolated 17-class dataset, preserving original source splits. Arthitaya
adds 480 supported images; Mees' lines remains a discriminator. Three newly confirmed
duplicate pairs include a pallor/melanonychia label conflict. Both sides are excluded
by `data/raw/goal60_exclusions_v3.json` (73 crops: TRAIN32/VALID30/TEST11). The initial
training run was stopped before any candidate deployment. Runtime crops were copied
to `goal60_runtime_crops_v3` and every source row rechecked; no TEST crops are used
for training or selection.

The restarted MobileNet candidate uses 23,184 TRAIN inputs including 9,585 runtime
crops (not independent subjects), with 1,480 VALID crops. It transfers compatible
weights from an earlier isolated candidate, aligning classifier rows by label, and
selects checkpoints by VALID macro recall. EfficientNet and nail-locator jobs are
serialized by `scripts/run_goal60_candidates.py`; endpoint evaluations use frozen
copies. TEST remains reserved for a fixed selection. Tiny melanonychia (VALID3) and
Lindsay (VALID6) pools remain provisional even if their point estimates pass.

The all-14 scorecard reports strict recall, healthy correct rate, balanced accuracy,
abstentions and Wilson intervals, including absent findings as misses. Tuner parity
is required before threshold selection; annotation-box results are labeled oracle
diagnostics. Missing-findings denominator handling was corrected in the tuner.

Verification: 212 ML/backend tests pass; frontend lint and production build pass.
Crop controls were exercised at 390x844, 375x667 and desktop viewport sizes, including
pointer dragging, keyboard resizing, normalized-coordinate confirmation and retake.
The goal remains unachieved pending the candidate endpoint and healthy-photo results.
The inherited MobileNet initialization used v1 quarantine; current TRAIN inputs
use v3, and all linked duplicate families are excluded from retained VALID/TEST.
Initialization weights and source training metadata remain auditable, rather than
being described as trained from scratch under v3.

Interim endpoint results: the fresh production VALID benchmark (1,350 source
photos, 311 healthy) meets the shown target for 3/14 signs; new MobileNet with
VALID-selected legacy rules meets 6/14 before the existing policy gates. It does
not meet the complete target. Learned localization reached 91.3% box recall and
83.0% precision on VALID at IoU>=0.5; these are not condition-detection results.
The first detector endpoint run rejected 615 photos as blurry. A VALID-only audit
of 60 rejected photos found 41 clear the unchanged focus threshold on the actual
15%-padded classifier crop, while no synthetically blurred version cleared it.
The ROI focus check now uses that same crop; the failed run and fresh reruns are
preserved. All four healthy phone crop modes remain free of pre-policy false
alarms for MobileNet plus detector on the existing single bootstrap subject.
Candidate ranking/final evaluation follows docs/goal60-selection-protocol.md;
TEST is untouched until the choice is frozen.


## 2026-09-24 — 60% per-condition goal, baseline and first candidate

Goal remains active and is NOT achieved. Operational target: strict per-condition detection recall >=60%, with false-positive rate and abstentions also reported; this is not clinical diagnostic accuracy. Geometry needs separately labeled paired side/top photos; the color harness cannot validate it.

Fresh VALID baseline through /analyze: 1,153 full source images, reduced to 1,128 after known-leakage quarantine. Shown strict recall: Beau 55.3%, cyanosis 56.9%, Muehrcke 58.3%, onychogryphosis 72.3%, pitting 60.7%, splinter 71.4%, Terry 50.0%. Pallor/leukonychia/onycholysis/Lindsay remain withheld (0% shown recall); no VALID melanonychia positives. Clinical images with simulated framing only. Old TEST numbers are not fresh evidence.

Audit of 15,819 color crops found 5 confirmed Ghana exact-duplicate TRAIN/VALID groups and 11 CHAA filename-family cross-split candidate groups. Quarantine expands linked Ghana patient groups, excluding 57 crops (train25/valid29/test3), preserving original splits and files. Manifest: data/raw/goal60_exclusions.json. No claim that near-duplicate/shared-patient leakage is fully ruled out.

Evaluation now counts inconclusive positives as misses, reports healthy correct rate/balanced accuracy, refuses unreadable-image omission, supports exclusion manifests and isolated model directories, and fingerprints new runs. Dataset helper imports no longer initialize Flask; each evaluation uses a unique scratch database. 173 ML/backend tests passed.

Separate CUDA environment ml/venv successfully exercised the RTX4060. A fresh ImageNet-initialized MobileNetV3-Large candidate is training for up to 30 epochs, selected by macro recall on VALID, with quarantine applied. Output: data/raw/goal60_candidate_models. No TEST evaluation or production replacement has occurred. Training launched via exec session 96326; first epoch macro recall 0.162. Existing uncommitted user work was preserved.

Next: finish candidate training, evaluate on quarantined VALID through /analyze, tune only on VALID, compare against baseline and retain guards. Research additional independently labeled minority-class data; do not treat pseudo-labels as ground truth. No candidate has earned deployment.


## 2026-09-24 — continued data audit

First candidate training is live (exec96326, PID14944; verified this turn), epoch4 VALID crop macro recall0.528; this is not end-to-end or per-condition success. No candidate weights deployed. Downloaded Taschenbier NailDiseaseClf v2 (969 images, declared CC BY4.0), but held it out: export merges melanonychia into other and onycholysis into naildystrophy, all samples are in valid, and contact-sheet inspection confirms third-party watermarks. Evidence: data/raw/candidate_naildiseaseclf_audit/review.json and target_contact.jpg. The source has not been ingested. Virtual E Dataset was also not used: its published description says labels were predicted by CNNs, so it cannot establish independent ground truth.

Added scripts/audit_color_near_duplicates.py: read-only cross-split dHash candidate generation, explicitly not proof of duplication. Audit running via exec91695; inspect candidate pairs before any additional quarantine. The first 57-crop manifest handles known exact/family overlap only.


## 2026-09-25 — first candidate complete; near-duplicate quarantine expanded

MobileNet candidate completed 30 epochs; metadata confirms best crop VALID macro recall 0.709799 and no TEST evaluation. Completed weights remain isolated in data/raw/goal60_candidate_models. Fresh GPU crop evaluation with TTA/temp and v2 exclusions: Beau26/47=55.3%, cyanosis38/65=58.5%, leukonychia5/5, Lindsay4/6, Muehrcke24/37=64.9%, onychogryphosis51/73=69.9%, onycholysis3/5, pallor251/342=73.4%, pitting38/61=62.3%, splinter48/52=92.3%, Terry150/175=85.7%. Tiny rare-class denominators and crop-only scope prevent success claims. Geometry-class crop outputs are not validation of geometry measurements. JSON: ml/eval/goal60_candidate_crop_valid.json.

Near-duplicate dHash audit: 2,434 candidate pairs, most not duplicates (including smooth Ghana thumbnails). Pixel comparison plus visual inspection confirmed 5 additional pairs: same nail/background with resizes/crops; one NIHATI splinter-labeled image matches an anemia pallor-labeled image (labels not clinically adjudicated). Reviewed evidence: data/raw/goal60_reviewed_duplicates.json and goal60_near_duplicate_top5.jpg. Exclusions v2 now67 crops: train29/valid30/test8. Existing source files/splits preserved; no automatic equivalence inferred from dHash alone. Scripts prepare_color_exclusions.py supports only explicitly confirmed reviewed pairs; 3 focused tests pass.

Full /analyze candidate VALID evaluation running, exec17527, cache ml/eval/goal60_candidate_valid.json, initially v1 exclusions. Filter completed cache with v2 before comparisons/tuning. Candidate run is diagnostic, not release-approved. EfficientNetB0 training launched on GPU, exec3262, 30epochs maximum, v2 exclusions, output data/raw/goal60_efficientnet_v2. No deployed weights or validation guards changed.

Tuner now accepts candidate manifest, exclusion manifest and explicit --min-recall0.60; preserves shipped gates. 10 decision-rule tests pass. Next: finish candidate endpoint evaluation, tune on VALID with v2 exclusions, compare against baseline; use resulting failure cases to select improvements. Do not evaluate TEST until final candidate/rules are fixed.


## 2026-09-25 — endpoint regression confirmed; training-domain experiment prepared

User confirmed no additional labeled data or clinician access available. Do not repeat the six previously exhausted source searches; missing/tiny minority-class and paired-side-photo evidence prevents verification of the full goal. Continue useful model experiments, without dropping conditions or weakening validation guards.

Candidate VALID endpoint evaluation completed (exec17527, exit0): 1128 examples with v1 exclusions; filtered both current/candidate caches with v2 for like-for-like report ml/eval/goal60_current_vs_candidate_v2.json. Candidate falls below60% strict recall on Beau42.6%, cyanosis53.8%, Muehrcke52.8%, splinter51.0%, Terry47.6%. Pitting63.9%, onychogryphosis75.4%; pallor pre-policy64.8% but healthy FP24.5%, remains withheld. Rare conditions remain withheld; no VALID melanonychia positives. No test set evaluated.

Real healthy bootstrap comparison (raw and guide-cropped, both current and candidate) is saved in ml/eval/goal60_healthy_pair_comparison.json. Current guide crop: zero outside findings; candidate falsely calls splinter hemorrhages outside (CNN0.570 versus healthy0.280), so candidate not deployed. Raw photos remain inconclusive. This is one prior bootstrap subject, not independent clinical performance evidence.

Candidate threshold tuner still running exec68620 (started before coverage-cache optimization); parity0mismatches. Early conditions remain mostly belowtarget after VALID-only tuning. Future tuner runs freeze manifest coverage once rather than reading JSON millions of times. 174 ML/backend tests passed.

Added scripts/build_runtime_color_crops.py to prepare an isolated experimental TRAIN/VALID dataset using production localization and CNN crop framing. Never processes TEST; skips ambiguous multi-label source images and logs failures. Source labels are inherited, not clinically verified; misses must still count in endpoint evaluation. Exact pixel parity with actual pipeline.predict_from_region input verified on three VALID source samples (pitting, Beau, healthy). Builder exec42601, PID5052, output data/raw/goal60_runtime_crops; 294 PNG crops observed at last check, process live. EfficientNet training exec3262, PID12824, reached epoch3 macroVALID0.429; output data/raw/goal60_efficientnet_v2. These are unfinished experiments, not achieved accuracy.
