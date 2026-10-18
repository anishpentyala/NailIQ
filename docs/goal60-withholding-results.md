# Withholding implementation results — October 3, 2026

## Outcome

Implemented the local validation and selection workflow. Displayed targets: **6/14**. Simulation with proposed permissions: **10/14**. The requested 12 displayed passes remain unachieved; simulations cannot clear withholding. No clinical grants, deployment, new labels or outreach occurred.

These are 1,350 existing VALID clinical/community source images with simulated framing, including 311 healthy images. They are development evidence, not independent patients or phone accuracy.

Strict displayed non-regression: **True**. Healthy scans with any outside result: **4/311**, against the frozen 6/311 anchor. Protected six routes and outputs remain fixed. Per-sign healthy correct counts do not fall and positive/healthy inconclusives do not increase.

Healthy scans with any inconclusive result: 311/311; all fourteen results within range: 0/311. Withheld conditions remain inconclusive; complete healthy-scan coverage is still absent.

Terry displayed recall improves from 50/155 (32.3%) to 76/155 (49.0%), with healthy Terry false alarms falling from 2/311 to zero. It remains below 60%. The four additional simulated permissions are clubbing, koilonychia, leukonychia and melanonychia; they remain withheld in actual results.

## Per-sign results

| Sign | Positive images | Displayed recall | Simulated recall | Displayed healthy FP |
|---|---:|---:|---:|---:|
| clubbing | 80 | 0.0% | 75.0% | 0/311 |
| koilonychia | 108 | 0.0% | 66.7% | 0/311 |
| leukonychia | 11 | 0.0% | 72.7% | 0/311 |
| melanonychia | 3 | 0.0% | 100.0% | 0/311 |
| pallor | 338 | 0.0% | 0.0% | 0/311 |
| cyanosis | 65 | 80.0% | 80.0% | 1/311 |
| terrys_nails | 155 | 49.0% | 49.0% | 0/311 |
| lindsays_nails | 6 | 0.0% | 0.0% | 0/311 |
| onycholysis | 11 | 0.0% | 0.0% | 0/311 |
| beaus_lines | 51 | 76.5% | 76.5% | 0/311 |
| muehrckes_lines | 36 | 72.2% | 72.2% | 1/311 |
| splinter_hemorrhages | 49 | 79.6% | 79.6% | 3/311 |
| pitting | 61 | 77.0% | 77.0% | 1/311 |
| onychogryphosis | 65 | 89.2% | 89.2% | 0/311 |

Hypothetical permissions selected: clubbing, koilonychia, leukonychia, melanonychia. These are proposals only. Other requested permissions stay withheld in the selected simulation.

## Implemented controls

- Scoped approval registry binds sign, model/weights, route, actual ROI mode, rules, evidence kind and relevant code. Missing or changed proof fails closed; reliable side geometry stays authoritative.
- Joint VALID selection counts the union of healthy false alarms. Withholding can remain per sign; low-confidence, failed and missing positives count as misses.
- Reviewed cohort import requires qualified sign assessments, retained first side/top pairs, rights references and patient grouping. Confirmation and development cannot overlap.
- Candidate/scopes/cohorts are locked before one-use fresh confirmation. Photo and patient claims prevent reuse by renaming a report. Full reference and current production are scored on the same patients.
- Specialist crop preparation uses reviewed development patients with explicit TRAIN/VALID groups and source controls. Confirmation data cannot train a specialist. No reviewed-data retraining occurred.

## Verification

- Backend and inference tests: 275 passed. Frontend lint/build passed; existing bundle-size warning remains.
- Full endpoint/replay: 1350 images, 18900 findings, 0 mismatches; unverified geometry 0.
- CPU/GPU subset: 64 images, 896 findings, 0 mismatches.
- One retained healthy phone subject in four capture modes: 56 findings, 0 mismatches; zero displayed and pre-policy false alarms on both devices.
- These checks establish local regression results only. No observed increase does not prove population equivalence.

The first joint winner failed the raw healthy-phone pre-policy check for melanonychia. Its partial endpoint run was stopped and is not a reported result. The previous melanonychia legacy route was restored; the rejected manifest, proposal, selection and failed phone report are retained under `data/raw/goal60_withholding_round3/rejected_phone_candidate`. The repaired endpoint was evaluated again.

## Remaining work

Qualified reviewers and permitted new patients/photos are still needed. Planning minima are 150 independently reviewed positives per claimed sign and 400 healthy patients, with adequate support for every proposed exact crop/evidence branch and source/tone subgroup. They are evidence gates, not a power calculation or guarantee.

Improve weak routes using reviewed development data, repeat strict endpoint checks, then freeze all choices before new confirmation. Further tuning after a failed confirmation requires fresh patients. Lindsay and onycholysis remain unresolved; melanonychia has only three current positive development images. Pallor proxy labels require visible-sign review. Top appearance cannot establish nail angle or spoon depth.

Protocol: [goal60-withholding-protocol.md](goal60-withholding-protocol.md). Local experiment: `data/raw/goal60_withholding_round3`; retained frozen bundle: `data/raw/goal60_withholding_frozen`.

Evidence: `selected.selection.json`, `ml/eval/goal60_withholding_selected_verification.json`, `goal60_withholding_device_parity.json`, `goal60_withholding_phone_parity.json`. Default production weights and policies remain in use; experimental adoption was not performed.
