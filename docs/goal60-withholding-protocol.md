# Withholding improvement protocol — October 3, 2026

The user selected strict preservation and external qualified review. Target: 12 of 14
displayed signs with strict recall >=60% and healthy FP <=5% per sign. Inconclusive,
failed and missing positive results are misses. All 14 signs remain reported; the
all-14 objective is still open. Historical TEST is archival, never fresh confirmation.

## Baseline and selection

The primary anchor is the immutable round-two selected displayed cache: 1,350 frames,
311 healthy, six passing signs, six healthy scans with any outside result. Keep
cyanosis, Beau, Muehrcke, splinter, pitting and onychogryphosis on their frozen routes,
rules and models. Existing regression verdicts/routes/evidence types must match.
Per-sign healthy correct results may not fall; positive and healthy abstentions may
not increase. There is zero extra-abstention allowance in this protocol.

`select_goal60_withholding.py` searches existing model/route alternatives, the prior
Terry floor/OVR/support grid, and pallor legacy floors .25–.90 in .05 increments.
Selection uses exact dynamic programming over unions of false-alarm image sets.
Reject per-sign FP >5%, scan unions >6/311 and coverage regressions. Maximize the
number of target signs passing, then summed recall, healthy correct counts and
simplicity. Protected signs and unresolved Lindsay/onycholysis stay frozen.

Default selection uses actual policy. `--propose-unlocks` is an explicitly marked
development simulation for the six additional signs; it never issues approval.
Each sign can retain current withholding. The selector chooses only the proposed
permissions that fit the shared healthy-scan budget; requesting six permissions
does not force six releases. It reports unmet targets explicitly.
Both actual and prospective results must preserve the anchor. Prospective success
does not establish displayed success. Development-selected permission scopes are
sealed before fresh confirmation; confirmation cannot discover or expand scopes.

## Scoped validation

Experimental grants bind the complete candidate semantic identity, condition,
configured route, actual ROI mode, effective decision rules and evidence kind:
appearance, measured color or ROI-only color. Identity includes model manifests,
weights/calibration/class mapping, locator and inference/acceptance code. Registry
and report paths are excluded from semantic identity to avoid hash cycles. Their
contents are checked separately, including revocation on cached runtimes.

An absent, malformed, edited or mismatched record keeps unsupported output withheld.
An exact grant cannot rescue blurry/blank photos, failed models, invalid boxes, low
confidence or guarded disagreement. Detector approval does not approve assisted or
legacy fallback branches. Appearance never supplies geometry values or overrides
reliable side measurements. Legacy production policy remains the default.

## Independent review and confirmation

Use the existing 9,998-reference review packets for development triage. Inherited
labels remain separate from qualified present/absent/indeterminate sign assessments.
Pallor needs visible-sign judgments; anemia status is retained separately. Record
reviewer qualifications, patient groups, photo adequacy, source, skin-tone band and
permitted-use reference. A healthy control requires all 14 signs reviewed absent.

The cohort importer requires retained side/top files and the first prescribed
capture pair for each confirmed patient group. It rejects unreviewed labels,
duplicate captures and development/confirmation overlap. Poor-quality known
positives remain in the denominator. Indeterminate sign labels are disclosed,
never invented. Exact existing dataset photos cannot enter fresh confirmation;
patient independence and near-duplicate adjudication additionally require reviewers.

Recruitment defaults are 150 independently reviewed positive patients per claimed
sign and 400 healthy patients. Grants require those counts and >=60% recall / <=5%
FP for their exact proposed evidence combination; multiple proposed crop branches
may require additional patients. These thresholds are a chosen evidence gate, not a
power calculation or a guarantee. All known source/tone cohorts must have controls
and must not conceal a >5% FP subgroup; unknown coverage cannot clear new grants.

Lock the candidate, exact scopes, full reference execution fingerprint, production
fingerprint, development cohort and fresh cohort before evaluation. Consumption is
recorded with exclusive per-photo claims in a fixed ledger, independent of output
filenames. Changing labels or renaming a lock cannot reuse scored photos.

Compare the full prospective endpoint with the frozen reference and actual current
production on identical patients. Require 12 target passes, protected performance,
healthy scan FP preservation, coverage, subgroup checks, endpoint replay, development
regression, exact CPU/GPU decisions and healthy-phone checks. Report confidence
intervals and paired discordance; no observed increase is not population equivalence.
After a failed confirmation, further tuning needs new independent patients.
Do not consume a fresh cohort to approve the present ten-target simulation. Its
pallor permission remains absent and Terry recall is below target. Obtain reviewed
development data, improve these routes, rerun joint selection and regenerate the
scoped proposal before scheduling a twelve-target confirmation.

## Workflow

Run the scripts from the repository root using the appropriate existing Python
environment. CPU is the default; the isolated GPU environment needs the backend
site-packages path added for YAML, as in the recorded round-two execution.

1. `prepare_goal60_withholding.py --out data/raw/goal60_withholding_round3` creates
   the isolated manifest, empty registry and empty development/confirmation templates.
2. Run `ml/eval/eval_end_to_end.py --split valid --routing-manifest <development.json>
   --exclusions data/raw/goal60_exclusions_v3.json --include-authorized
   --include-shapes --cache <development-cache.json>`.
3. `select_goal60_withholding.py --cache <development-cache.json> --manifest
   <development.json> --reference ml/eval/goal60_round2_selected_gpu_valid.json
   --out <selected.json> --propose-unlocks` produces actual/prospective checks and
   an exact development scope proposal in `<selected.contexts.json>`.
4. Re-evaluate the selected endpoint; run the existing parity, round-two verification,
   device and four-mode phone checks. New outputs bind the candidate bundle hash.
5. Obtain reviewed paired cohorts; `evaluate_goal60_confirmation.py lock --candidate
   <selected.json> --reference <frozen-reference.json> --development <reviewed-development.json>
   --cohort <fresh-confirmation.json> --context-plan <selected.contexts.json> --out <lock.json>`.
6. Run its `run` action with the same inputs, `--lock <lock.json> --regression
   <verification.json> --device <device-parity.json> --phone <phone-result.json>
   --out <confirmation-report.json>`. Files remain private local evaluation artifacts.
7. Only a fully passing report permits its `issue --candidate <selected.json>
   --report <confirmation-report.json> --out <validation-evidence.json>` action.
   Freeze includes records/reports and checks semantic identity after relocation.
   Verify the approved endpoint before production adoption; preserve rollback.

For reviewed specialist training, preassign development patients with
`development_split: train|valid`. Run `build_goal60_reviewed_specialist.py --cohort
<reviewed-development.json> --condition pallor --out <new-crop-directory>`, then
the existing color trainer with `--data-dir <new-crop-directory> --condition pallor
--source-matched --backbone efficientnet_b0 --epochs 20 --batch-size 16 --workers 2
--output-dir <new-isolated-model-directory>`. Repeat the endpoint selection protocol;
the builder never reads confirmation data or guesses a visible-sign label. Its
binary healthy class means reviewed target absence, including other co-occurring
signs; it does not redefine the endpoint healthy control cohort.

No clinician, new reviewed patient cohort or photo access has been arranged by this
implementation. The five existing access drafts remain unsent.
