# NailIQ image-verifier results — October 4, 2026

Displayed target on the retained selected-reference development benchmark: **6/14**. Goal12 and all14 remain unproved.

Completed four EfficientNet-B0 development runs, seeds42/1337 per sign,
maximum20 epochs. Partial published-label crop/evaluation adapters and
truthful side-view/Hb checks are implemented. No newly qualified source
cohort was acquired, no release grants were written, and the app is unchanged.

Combined candidate rejected: Terry's nails 58.1%, pallor proxy 15.7%; pallor adds 1 per-sign healthy flag despite an unchanged scan union.

| Sign | Actual shown recall | Hypothetical shown recall | Hypothetical healthy flags | Status |
|---|---:|---:|---:|---|
| beaus_lines | 76.5% (39/51) | 76.5% (39/51) | 0/311 | >=60% observed |
| clubbing | 0.0% (0/80) | 0.0% (0/80) | 0/311 | target unmet |
| cyanosis | 80.0% (52/65) | 80.0% (52/65) | 1/311 | >=60% observed |
| koilonychia | 0.0% (0/108) | 0.0% (0/108) | 0/311 | target unmet |
| leukonychia | 0.0% (0/11) | 0.0% (0/11) | 0/311 | target unmet |
| lindsays_nails | 0.0% (0/6) | 0.0% (0/6) | 0/311 | target unmet |
| melanonychia | 0.0% (0/3) | 0.0% (0/3) | 0/311 | target unmet |
| muehrckes_lines | 72.2% (26/36) | 72.2% (26/36) | 1/311 | >=60% observed |
| onychogryphosis | 89.2% (58/65) | 89.2% (58/65) | 0/311 | >=60% observed |
| onycholysis | 0.0% (0/11) | 0.0% (0/11) | 0/311 | target unmet |
| pallor | 0.0% (0/338) | 15.7% (53/338) | 1/311 | target unmet; shadow only, no display permission |
| pitting | 77.0% (47/61) | 77.0% (47/61) | 1/311 | >=60% observed |
| splinter_hemorrhages | 79.6% (39/49) | 79.6% (39/49) | 3/311 | >=60% observed |
| terrys_nails | 49.0% (76/155) | 58.1% (90/155) | 0/311 | target unmet; shadow only, no display permission |

Hypothetical passes: 6/14; actual shown passes remain 6/14.
Healthy scans with any flag: 4/311 hypothetical vs 4/311 reference.
New healthy scan flags: 0. New per-sign healthy flags: {'clubbing': 0, 'koilonychia': 0, 'leukonychia': 0, 'melanonychia': 0, 'pallor': 1, 'cyanosis': 0, 'terrys_nails': 0, 'lindsays_nails': 0, 'onycholysis': 0, 'beaus_lines': 0, 'muehrckes_lines': 0, 'splinter_hemorrhages': 0, 'pitting': 0, 'onychogryphosis': 0}. Strict preservation: False.

## Verification

- Backend/inference verification: 307 tests passed.
- Fresh endpoint: 36 images, 504 findings; 0 mismatches.
- Crop comparisons: 0 endpoint mismatches; 32 retained training/calibration checks, 0 mismatches.
- New verifier CPU/GPU decisions: 0 mismatches; maximum rounded probability difference 0.0.
- Existing healthy phone subject: one subject, four modes; hypothetical flags [[], [], [], []]. This is a bootstrap regression, not population evidence.
- Blur, dark lighting, glare, blank and invalid-image mutations: 0 hypothetical positives.

## Evidence limits and rejected outcomes

- Available Terry labels are community assessments; pallor labels are anemia/Hb proxies.
  Neither is newly independently qualified visible-sign ground truth.
- Hb-normal proxy negatives cannot establish absence of Terry or all14 signs.
  Healthy-FP results apply to the inherited development benchmark only.
- TRAIN fit/calibration/omitted groups use known family IDs and exact image/crop
  duplicates. Unknown patient relationships may remain. The first-stage model
  ancestry has seen original TRAIN, so omitted cohorts only test the verifier.
- Historical VALID is a reused development benchmark. Models, thresholds,
  code and inputs were frozen before this diagnostic; no threshold was selected
  on historical TEST or this new VALID comparison.
- Inconclusive, missing and failed positive photos count as misses. Per-sign
  recall/FP intervals, healthy correct/abstention counts, source/tone results
  and omitted-cohort diagnostics are retained in results.json.
- One original Terry calibration produced NaN; it is retained as unusable.
  The separate finite bundle fits bounded temperature on the same TRAIN-derived
  calibration using inference-matched horizontal flips. A pallor replica reaches
  the temperature boundary, indicating weak discrimination; this is reported.
- The cutoff writer stopped on a relative file path after all5122 images were
  scored. Original image/label membership and weights were rechecked, and
  retained TRAIN scores were used to finish freezing; no VALID choices changed.
- Malformed uploads are tested through the API, which rejects them with
  HTTP400. Well-formed encodings of non-image bytes remain invalid-image misses.
- The shadow checker cannot create clinical grants. Improvements to two signs
  do not approve clubbing, koilonychia, leukonychia or melanonychia display.
- Lindsay and onycholysis remain explicitly reported, with their small original
  positive counts. Unmeasured or withheld signs cannot disappear from the goal.

## Existing-data requests

Both [Terry request](goal60-terry-data-request.md) and
[SEWA request](goal60-sewa-data-request.md) have verified published recipients.
Requests remain UNSENT pending explicit sending approval. SEWA gated contact
sharing and data-agreement acceptance are separately unapproved. No account
details were submitted. No qualified local technician is needed for these requests.

## Reproducibility and rollback

Experiment: data/raw/goal60_image_round5_verified.
Models lock SHA256: 0681814ed1de766df6165a14bcef1e1852d33cec9a0589103cdf2a289a9df486.
Thresholds lock SHA256: b2dd8726881f95503a14731f79bb7149100511266f5fc89a902ab178aa9140b8.
Results SHA256: 19292a70d3936e8ecbeabbc5e46a933f0e9ec82c0e348216273598fe02dfcd72.
All original runs and rejected calibrations are retained. Production weights,
public /analyze API and display gates were not edited. Stop referencing these
isolated experiment files to roll back research use.

See [implementation protocol](goal60-image-verifier-protocol.md).
