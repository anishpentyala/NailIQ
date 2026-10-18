# Training repair results — October 4, 2026

Fixed the initialization-heavy moving average used during color-model training.
The first optimized state now replaces the random starting state, and averaging
strength increases with training updates. Selected epoch/update counts and the
initial-state contribution are recorded. Geometry training and inference are unchanged.

Three previous selected checkpoints retained 98.31–98.51% of their initialization;
the fourth retained 71.16%. The repaired runs retain zero initial-state contribution.
These are averaging weights, not percentages of correct predictions.

| Model | Seed | Prior calibration macro recall | Repaired calibration macro recall | Selected epoch | Updates |
|---|---:|---:|---:|---:|---:|
| terrys_nails | 42 | 65.1% | 91.2% | 20 | 340 |
| terrys_nails | 1337 | 64.6% | 90.0% | 11 | 187 |
| pallor | 42 | 56.4% | 60.4% | 8 | 120 |
| pallor | 1337 | 51.1% | 60.9% | 18 | 270 |

Calibration measures localized crops on the fixed TRAIN-derived calibration cohort.
Both data manifests are byte-identical to the prior run; shared rounded training-loss
trajectories match in all runs: True.

Actual displayed benchmark remains **6/14**.
Experimental hypothetical passes: **7/14**; no clinical grants.

| Sign | Actual shown recall | Prior experiment | Repaired experiment | New healthy flags |
|---|---:|---:|---:|---:|
| beaus_lines | 76.5% (39/51) | 76.5% (39/51) | 76.5% (39/51) | 0 |
| clubbing | 0.0% (0/80) | 0.0% (0/80) | 0.0% (0/80) | 0 |
| cyanosis | 80.0% (52/65) | 80.0% (52/65) | 80.0% (52/65) | 0 |
| koilonychia | 0.0% (0/108) | 0.0% (0/108) | 0.0% (0/108) | 0 |
| leukonychia | 0.0% (0/11) | 0.0% (0/11) | 0.0% (0/11) | 0 |
| lindsays_nails | 0.0% (0/6) | 0.0% (0/6) | 0.0% (0/6) | 0 |
| melanonychia | 0.0% (0/3) | 0.0% (0/3) | 0.0% (0/3) | 0 |
| muehrckes_lines | 72.2% (26/36) | 72.2% (26/36) | 72.2% (26/36) | 0 |
| onychogryphosis | 89.2% (58/65) | 89.2% (58/65) | 89.2% (58/65) | 0 |
| onycholysis | 0.0% (0/11) | 0.0% (0/11) | 0.0% (0/11) | 0 |
| pallor | 0.0% (0/338) | 15.7% (53/338) | 1.2% (4/338) | 0 |
| pitting | 77.0% (47/61) | 77.0% (47/61) | 77.0% (47/61) | 0 |
| splinter_hemorrhages | 79.6% (39/49) | 79.6% (39/49) | 79.6% (39/49) | 0 |
| terrys_nails | 49.0% (76/155) | 58.1% (90/155) | 69.7% (108/155) | 0 |

Healthy scans flagged: 4/311, versus 4/311 reference.
All previous correct positives preserved: True. Strict preservation: True.
A new per-sign healthy flag rejects the combined candidate even if it affects an already flagged scan.

## Verification

- 319 backend/inference tests passed; failures/errors 0/0.
- Endpoint: 36 images, 504 findings; mismatches 0.
- Crop mismatch counts: endpoint 0, retained 0/32.
- CPU/GPU decision mismatches: 0; largest rounded probability difference 0.0.
- One healthy phone subject, four modes: hypothetical flags [[], [], [], []].
- Stress-test hypothetical positives: 0; malformed upload status 400.
- Overall engineering verification passes: True.

- Reused first-stage cache: 21 fresh comparisons matched first-stage verdicts and crop/quality extraction.

Calibration scores are now bound to their exact model bundle, evidence and collector code;
recovery rejects changed scores or models. Training source hashes are frozen and verified.

## Remaining limits

All fourteen denominators include failed localization, withheld results and abstentions.
This is one fixed development experiment, with choices frozen before the reused VALID
diagnostic. No threshold was selected on that diagnostic or historical TEST.
Source/tone breakdowns, intervals and stage-two omitted-cohort results remain in results.json.
The first-stage model ancestry has seen original TRAIN; omitted images are not independent
confirmation of the entire pipeline. Unknown patient relationships may remain.

Terry labels remain community assessments. Pallor labels remain anemia/Hb proxies,
not qualified visible-pallor assessments; proxy negatives do not establish all14 signs absent.
One healthy phone subject does not measure population accuracy. The repair cannot create
clinical display permission or establish 12/14 or all14 readiness. Existing-data request
drafts remain unsent and gated terms unaccepted.

## Reproduction

Experiment: `data/raw/goal60_image_round6_ema_repair`.
Protocol: [training repair](goal60-training-repair-protocol.md).
Production manifest SHA256: `c419d567ae7272dc0e5f1c07a50c2fbe2a1c7c4c0d5fdc71ad08e5111e96c420`.
Models lock SHA256: `41de5b5a1ac697fd8b9fce74971b74be080905470d2be47cb3ee208bd03acbce`.
Thresholds lock SHA256: `2836ceba903c83edc76d9a8daa7c81ff995b550179d9af79cd4844a1c3c1fb46`.
Results SHA256: `cb0f8810b2a4347d57e5bf1f0376ffe24606289c359df5230cc4547fb3be3061`.
Prior artifacts remain retained; edited prior source is preserved in
`data/raw/goal60_training_repair_source_before`. No production weights were replaced.
