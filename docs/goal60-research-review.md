# Research review and next experiments

Reviewed October 2, 2026. Status: proposed work; no new model performance established.

This is a targeted verification of the user-supplied research report, not an exhaustive
verification of every paper, contact or dataset in it. The frozen all-14 result remains
6/14 passing the dataset recall/false-alarm limits; production weights are unchanged.

## Findings that change the plan

| Lead | Verified status | Next action |
|---|---|---|
| FAU/Charite nail-psoriasis study | Data and architecture offered by request. Methods score pitting, crumbling and onycholysis; leukonychia labels and masks are unconfirmed. Cohort counts are internally inconsistent. | Ask for original images, patient grouping, component labels, diagnosability flags and permitted uses. |
| Lindsay's 104-patient study | The missing reference is resolved: DOI 10.1111/ijd.70302, published January 21, 2026. The publisher identifies Jacek C. Szepietowski as corresponding author and says underlying data are available on reasonable request. The number of positive photographed patients is unconfirmed. | Ask whether original nail photographs exist, how many patients have the sign, and whether images and labels can be shared. Do not count 104 as 104 positive cases. |
| Weill Cornell melanonychia cohort | The abstract reports 248 benign cases: 47 biopsied and 201 nonbiopsied patients. This does not establish 248 available photos or permission to access them. | Ask for ordinary clinical photos, grouping keys, sign annotations, capture metadata and permission. Verified contact: Shari Lipner, shl9032@med.cornell.edu. |
| Balearic segmentation study | The authors explicitly state that the database must remain private and that both images and code belong to the company. They also acknowledge selecting a classifier using the test set. | Remove it from the available-data shortlist. Its methods can inform experiments; the reported score is not independent transfer evidence for NailIQ. |

Primary sources: [FAU/Charite](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2025.1574413/full),
[Lindsay study and corresponding author](https://onlinelibrary.wiley.com/doi/10.1111/ijd.70302),
[Cornell cohort](https://pubmed.ncbi.nlm.nih.gov/35752275/),
[Balearic ownership and limitations](https://arxiv.org/html/2501.06027v1#S4.SS2).

FAU's abstract/table report 460 patients/4,400 images plus independent 118/929;
other passages give conflicting totals. Its validation excludes non-diagnosable
photos and covers Fitzpatrick I-III, limiting comparability with NailIQ. Internal
training/test patient grouping is not established. The [corrigendum](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2025.1617441/full)
corrects an author name, not these counts. It confirms contact Filippo Fagni,
filippo.fagni@uk-erlangen.de. None of these access leads is a newly acquired dataset.

## What to keep and what to correct

Keep condition-specific experiments, clinician annotation, patient grouping, explicit
unknown labels, healthy abstention reporting and fresh confirmation after model freeze.
The report's diagnoses of the failures are hypotheses except where our own endpoint
audit directly demonstrates a blocked measurement. It has not proven that illumination
or missing geometry is the dominant cause of every weak sign.

NailIQ already has side geometry, signed spoon-nail curvature, geometry/CNN fusion,
all-14 reporting, intervals and a scan-level false-alarm metric. Improve and validate
these components rather than rebuilding them as if absent. New learned landmarks need
repeatability evidence and must not turn top-photo appearance into a claimed angle.

Visible pallor and hemoglobin/anemia remain separate targets. A new visual annotation
task requires its own baseline; changing the labels cannot be presented as improving
the old anemia-proxy benchmark. Use TRAIN/VALID material for development annotations,
not the 364 already evaluated TEST positives. Dataset/source names should be used for
auditing and matching controls, not casually added as predictive features unavailable
or misleading in an ordinary user scan.

Patient counts are not independent image counts. Enriched clinical recruitment helps
obtain positives, but severity and case mix can change sensitivity and specificity.
It does not by itself establish performance in ordinary users. See the discussion of
enriched datasets in this [primary study protocol](https://bmjopen.bmj.com/content/12/1/e054005).

The suggested sample sizes are planning assumptions, not guarantees. Recalculation:

| Check | Result |
|---|---:|
| Terry healthy FP 12/239, two-sided Wilson 95% interval | 2.895%-8.570% |
| 2 FP / 124 healthy, one-sided exact 95% upper bound | 4.990% |
| 9 FP / 300 healthy, one-sided exact 95% upper bound | 5.177% |
| 73/107 recall, one-sided exact 95% lower bound | 60.033% |
| 46/65 recall, one-sided exact 95% lower bound | 60.123% |

Thus 300 healthy cases with 3% observed FP do not quite put the one-sided upper bound
below 5%. Per-sign 95% intervals also do not jointly establish a 95% all-14 claim.
Do not change the previously agreed point-estimate acceptance target retrospectively;
record any additional confidence-bound criterion before a new confirmation study.

## Recommended order

1. **Cheap development experiments first:** condition-specific localization and Terry
   calibration. Compare strict recall, healthy correct rate, abstention and source-level
   FP. The alternative clubbing route reached 51/80 validation positives versus 37/80,
   but healthy correct classifications fell from 230/311 to 207/311. This is a tradeoff,
   not a ready-to-deploy improvement. Use a recorded healthy-coverage constraint.
2. **Measurement feasibility:** prepare TRAIN/VALID annotation packets for Lindsay's
   proximal/distal zones and onycholysis nail/affected-area masks. Test whether expert
   annotations are reproducible and whether measurements separate positives from
   explicitly labeled mimics. Existing disagreement safeguards remain until better
   measurement evidence is validated; a second model vote is not automatically
   independent corroboration.
3. **Pallor specialist and label audit:** source-matched controls, separate visible-sign
   annotations, and photometric ablations. Do not merge unassessed signs into negatives.
4. **Shape and rare-sign acquisition:** repeated paired side/top captures for geometry;
   clinician-reviewed leukonychia/melanonychia and ordinary-phone healthy controls.
   Flash/no-flash capture remains a research hypothesis requiring a paired-photo pilot.
5. **Freeze and confirm:** new patient-separated evidence, frozen model/rules, actual
   `/analyze` runs for all 14, healthy-photo regressions, strict denominators and directly
   measured scan-level false alarms. The old TEST remains a historical benchmark.

Selection evidence: `ml/eval/goal60_final_selection.json`.
Current results: [goal60-results.md](goal60-results.md).

## Ready-to-send Lindsay data inquiry

To: Jacek C. Szepietowski, jacek.szepietowski@pwr.edu.pl

Subject: Research inquiry about nail photographs from your 104-patient half-and-half nail study

Dear Professor Szepietowski,

I am developing NailIQ, a precautionary nail-photo screener that reports visible nail
findings without diagnosing underlying disease. Your 2026 study of half-and-half nails
is relevant to our work on detecting the visible proximal/distal color pattern.

Does the study retain original nail photographs with clinician assessments? If so,
could you clarify the number of patients photographed, the number with confirmed
half-and-half nails, and whether deidentified images and assessments could be shared
for a research pilot?

Anonymous patient grouping, nail/view identifiers, uncertain assessments and available
capture metadata would help us keep evaluation independent. We would also appreciate
the applicable terms for model training, derived annotations, aggregate publication
and distribution of trained weights. We would not redistribute the original images
without explicit permission.

Thank you for considering this request.

## Clarifications to add to the FAU data inquiry

Request corrected counts, patient/cohort manifests, original photos and individual
component labels. Ask separately whether leukonychia annotations or affected-area
masks exist. Total severity scores cannot supply missing component labels.

No messages have been sent. No new data have been obtained. This review does not
establish improved detector accuracy or authorize production deployment.
