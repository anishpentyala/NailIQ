# Published-label audit — October 4, 2026

No new verification cohort was acquired. This audit inspected public metadata/card
documentation only. No images downloaded, gated files accessed, agreements accepted,
contact details shared, or messages sent.

## Google SCIN

Primary sources: [repository](https://github.com/google-research-datasets/scin),
[schema](https://github.com/google-research-datasets/scin/blob/main/dataset_schema.md),
[licence](https://github.com/google-research-datasets/scin/blob/main/LICENSE).

The public CSVs contain 5,033 cases and 20 self-reported NAIL_PROBLEM cases. A
case-insensitive exact-sign-name audit of dermatologist labels finds:

| NailIQ sign | Cases | Assessment |
|---|---:|---|
| Leukonychia | 1 | confidence 5, differential weight 0.55 |
| Muehrcke lines | 1 | same case; confidence 4, weight 0.23 |
| Pitting | 1 | different case; confidence 4, weight 0.21 |
| Other eleven signs | 0 explicit matches | synonyms/images could differ; no established coverage |

The leukonychia/Muehrcke case has one image and foot-top-or-side metadata. The
pitting case has two images, an unspecified site, and nail dystrophy has a higher
differential weight (0.29). These are possible differential diagnoses, not exhaustive
present/absent judgments for all fourteen signs. Neither omitted signs nor the
self-reported LOOKS_HEALTHY category establish verified negative labels. These two
cases cannot clear withholding or supply sufficient Terry/pallor positives.

Metadata-only reproduction:
- https://storage.googleapis.com/dx-scin-public-data/dataset/scin_cases.csv
  SHA256: 7923ee9ba9775af413ca115c4587dc1bd32259d7936aa97fa80d88dd616ca3c3
- https://storage.googleapis.com/dx-scin-public-data/dataset/scin_labels.csv
  SHA256: 616ad03c24c304f5f7ef01b4116e4d3274f1c71c9b19a0e3d5620698b081a9fe

SCIN's custom licence allows reproduction/adaptation with attribution, retained
notices, disclosure of modifications, no implied endorsement and no reidentification.
Actual ingestion must preserve those terms. No images are imported in this run.

## SEWA Rural

[Official card](https://huggingface.co/datasets/sewa-rural-care/anemia-survey-data)
lists open/closed-finger nail photographs, participant UUIDs, nail_examination,
nail_examination_other, polish/henna fields, haemoglobin and camera metadata.
Open/closed finger poses are not confirmed paired side/top captures.

The card does not provide examination value vocabulary, assessor qualifications,
agreement, completeness or visible-pallor-positive counts. Laboratory haemoglobin
verifies anemia, not visible nail pallor. Code examples differ from some claimed
normalized column names; actual schema/label-image correspondence need auditing.

Access is gated: login, contact-information sharing and Data Access Agreement.
CC-BY-NC-4.0 plus additional terms limit use to noncommercial scientific/academic/
educational work, prohibit raw redistribution without permission and require credit.
Commercial use needs written permission. Do not include raw data in source/vault
archives. A request for access is pending user authorization, not completed access.

This is a possible pallor lead, not acquired data or confirmed expert sign evidence.
No direct new expert-labelled Terry source was established in these two sources.
Existing excluded/contaminated corpora remain excluded. Model-generated labels
cannot establish independent ground truth.

## Stronger Terry lead: existing physician assessments

[Nelson et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6025669/)
photographed fingers/toes of 503 outpatients. Four trained physicians independently
recorded Terry's nails as present, absent or indeterminate while blinded to medical
history and one another. This is a direct sign-assessment design, unlike an anemia
proxy or SCIN differential. Reported finger-sign inter-rater kappa was 0.56; agreement
and indeterminate cases must be preserved rather than choosing convenient labels.

The public article contains one illustrative figure, not a downloadable 503-patient
image/assessment dataset. Positive prevalence reported as 3–8% is not an exact
consensus-positive count. Cohort access, reuse rights, patient grouping and counts
remain unconfirmed. Do not infer permission from public PMC text or treat it as
newly acquired data. A prepared request is in goal60-terry-data-request.md; unsent.

This offers a way to obtain already-completed review remotely if the authors can
share permitted de-identified data; it does not require Anish to recruit a reviewer.
