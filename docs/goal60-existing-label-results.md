# Existing-label alternative: results — October 4, 2026

**Displayed goal remains 6/14.** No production model/rule changes, clinical grants,
new clinical labels, deployment or outreach occurred. The October 3 isolated
reference remains 4/311 healthy scans flagged and Terry recall 76/155 (49.0%).
A source-file/weight hash check confirms its endpoint dependencies are unchanged.

The user cannot arrange qualified review. Implemented a research importer for
already-published expert sign assessments, allowing partial labels and truthful
top-only/unknown views without asking for new reviews. Unassessed signs stay
unknown; anemia is not visible pallor; partial-negative records are not all-sign
healthy cases. This importer does not write release grants.

## Completed engineering experiment

Processed 8,297 original full-image records: 6,947 TRAIN and 1,350 VALID.
Automatic localization uses the same preprocessing, framing simulation, glare,
polish and blur checks as the app. Failed localization remains in denominators.
TRAIN group calibration selected forest depth and score threshold before VALID
scoring. Two depths per sign plus two source-holdout models were trained (six total).
Known source families/Ghana keys and exact-byte copies share calibration groups.
No known TRAIN/VALID group or exact-byte overlap required additional quarantine.
Existing exclusions retained; unknown patients/perceptual duplicates remain a limitation.

Features include skin-relative redness, brightness-normalized longitudinal zones,
saturation and proximal/distal white-band patterns. The inherited skin reference
is an estimate, not verified skin segmentation. Forest vote fractions are not
calibrated clinical probabilities. OpenCV minSampleCount=12 controls node splitting;
the protocol phrase "minimum leaf sample count" is imprecise, not a leaf-size guarantee.

## Proposed displayed rescues, before any permission

These are hypothetical positive-only additions to the actual displayed reference,
**not deployed app results**. Every option was fixed on TRAIN calibration.

| Sign | TRAIN calibration FP budget | Proposed caught / positives | Recall | New healthy sign flags | Healthy scans flagged |
|---|---:|---:|---:|---:|---:|
| Terry's nails | 0% | 77/155 | 49.7% | 0 | 4/311 |
| Terry's nails | 1% | 81/155 | 52.3% | 1 | 5/311 |
| Terry's nails | 3% | 94/155 | 60.6% | 10 | 14/311 |
| Terry's nails | 5% | 101/155 | 65.2% | 18 | 22/311 |
| Pallor proxy | 0% | 0/338 | 0.0% | 0 | 4/311 |
| Pallor proxy | 1% | 12/338 | 3.6% | 0 | 4/311 |
| Pallor proxy | 3% | 30/338 | 8.9% | 2 | 6/311 |
| Pallor proxy | 5% | 70/338 | 20.7% | 16 | 20/311 |

Terry reaches 60.6% only with ten new healthy flags; that challenger is rejected.
The strict zero-new-flag Terry rescue adds one development hit (49.0% -> 49.7%).
The 1% TRAIN-budget pallor challenger adds twelve hypothetical displayed proxy hits
(3.6%) with zero new healthy flags, still far below target and unsupported as a
visible-pallor finding. Small development gains do not justify production adoption.
Protected six routes/decisions and all withholding policies remain unchanged.

The original results.json and budget-results.json compare pre-policy predictions.
Their pallor baseline134/338 is **hidden**, not displayed. Use display-preservation.json
for the shown baseline0/338 and shared healthy-scan4/311 comparison. A regression
test rejects using hidden "verdict" when the explicit "shown" field is unavailable.

## Cross-source robustness

| Research model | Entire omitted source | VALID caught / positives | Healthy flags |
|---|---|---:|---:|
| terrys_nails | yolov8-nails-segmentation-ckvkd | 0/63 | 0/33 |
| pallor | fingernails-ghana-anemia | 4/229 | 0/186 |

These source-held-out feature models separate the labels poorly. This is evidence
against relying on these colour/spatial features alone; it is not evidence that
a threshold change resolves withholding. Current VALID is reused development data,
clinical/community images have simulated framing, and historical TEST was not used.
No new independent clinical or phone sensitivity result is claimed.

## Published-label work

- SCIN public metadata audited: 5,033 cases, twenty self-reported nail cases.
  Only two distinct cases mention exact target signs (leukonychia/Muehrcke in
  one case, pitting in another). Differential possibilities cannot clear withholding.
- SEWA Rural is an unverified possible pallor source. Local CSV/JSON/Parquet
  schema/vocabulary auditing is ready. Gated access/contact sharing/terms acceptance
  remain pending explicit authorization. No account information was submitted.
- Nelson2018 photographed503 patients with four blinded physician Terry assessments.
  No downloadable image/assessment cohort was found. An existing-data request is
  prepared and **unsent**; acquisition and rights remain unconfirmed.

See [source audit](goal60-published-label-audit.md), [unsent Terry request](goal60-terry-data-request.md),
[engineering protocol](goal60-existing-label-protocol.md) and [budget protocol](goal60-feature-budget-protocol.md).

## Verification and retained evidence

- 286 backend/inference tests passed, including feature/vote, grouping, missing-data,
  partial-label, duplicate-patient and hidden-versus-shown protections.
- Frozen model/threshold and input hashes checked before scoring. Same1,350 VALID
  image/label identities verified against the original endpoint cache.
- No endpoint integration of challengers or new phone test was needed: none clears
  both the target and preservation gate. Existing phone results remain bounded
  one-subject evidence, not a fresh validation result.
- Earlier feature caches are retained. Selection stopped on a stale bookkeeping
  fingerprint; a later comparison stopped on Windows/POSIX path separators.
  Rebuilt the final verified cache rather than altering previous frozen metadata.
- Final experiment: data/raw/goal60_feature_round4_verified. Public-source audit:
  data/raw/goal60_feature_round4/published-label-audit.json.

Model/threshold lock SHA256: `b7d5c85f5bc4bec44fe9beec3f5474198588bdb8d49213988dbedd0d096b4438`.
Displayed comparison SHA256: `4bab98f425e825663b78ee87be9a922788634cc58916a8383988d439bfe9dc24`.

## Next actions without recruiting a reviewer

Pursue permitted access to already-assessed data and audit original sign-label
vocabulary/provenance. The prepared importer accommodates those partial labels
for research without inventing all-sign negatives or side views. Use eligible
new sources to train a stronger image model and evaluate the actual endpoint.
Published labels can substitute for commissioning review within their documented
scope; they cannot establish unsupported views, all-sign healthy status or phone
accuracy. No guarantee of12/14 or all14 follows from the current evidence.
