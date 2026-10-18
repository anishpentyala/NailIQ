# Clinical review and data-access packet

Prepared October 2, 2026. Drafts only: no messages sent or new data received.

## Local annotation work

`data/raw/goal60_round2_review/images.jsonl` indexes 9,998 TRAIN/VALID images
(8,975 TRAIN, 1,023 VALID). There are zero new clinical labels; every sign is
`not_assessed`. `review.csv` and `task.json` in each of eight sign folders specify
the first review workload. Local contact sheets show image IDs and split; original
images remain in their source folders. Coordinates refer to original full images.

These are images, not 9,998 independent patients. The Lindsay contact sheet visibly
contains repeated appearances. Existing source labels are suggestions requiring review;
normal/anemic labels do not establish visible pallor, and one label does not establish
the absence of other signs. Confirm duplicate/patient groups before creating cohorts.
Four specialist crop-VALID files use the misspelled source token `Anmeic_fn_009`.
They inherit a pallor/anemia-proxy training label, while the frozen full-image benchmark
recognizes neither that token nor its clinical truth and excludes them. This explains
233 specialist crop positives versus 229 Ghana benchmark positives; the crop score and
endpoint score are different pools. `unresolved_label_examples.json` records these
four images for review without changing the frozen benchmark or inventing new labels.
The current preview is for engineering triage; blinded clinical assessment should hide
inherited labels and algorithm outputs. Preserve disagreement and indeterminate cases.

Qualified reviewers should assess all eight signs independently as present, absent or
indeterminate; assess photo adequacy separately; record reviewer and adjudication.
Annotate whole-nail boundaries, orientation/cuticle/free-edge landmarks, affected
onycholysis polygons and Lindsay proximal/distal zones as specified in each task file.
Review glare, polish, nail injury and co-occurring signs. Patient grouping, skin-tone
coverage, device/view and permitted reuse must be checked before subsequent training.

`ml/infer/review_measurements.py` computes affected-area fraction and proximal/distal
color contrasts from reviewed polygons. It has no thresholds, diagnostic verdicts or
production integration. Synthetic-mask tests establish arithmetic only. Fit measurements
on reviewed TRAIN; development evaluation on grouped VALID; fresh patients for final
confirmation. Preserve inconclusive results in the denominator.

After review, copy the index to a separate reviewed JSONL file. Add `nail_polygons`
to the image row; add `affected_polygons` under the reviewed onycholysis sign, and
`proximal_polygons`/`distal_polygons` under Lindsay's. Each polygon is a list of
normalized `[x,y]` points. Record per-sign `reviewer` and `status`; do not overwrite
the unreviewed source index. Run `scripts/measure_reviewed_nails.py --reviews <file>
--out <measurements.json>` with the backend Python. Unreviewed rows or missing masks
are skipped. The output retains reviewed labels and raw measurements, not predictions.

Fresh confirmation recruitment target: 150 positive patients per sign and 400 healthy
patients, with diversity, paired side/top photographs and independently adjudicated
signs. This is a planning target, not a guarantee of performance or statistical power.
One patient may contribute several signs but stays in one split; repeated photos do not
increase the independent patient count. Get institutional/clinical supervision and
consent before collection. No clinician has been arranged.

## FAU / Charité draft

To: Filippo Fagni, filippo.fagni@uk-erlangen.de

Subject: Research access inquiry: original nail photographs and component assessments

Dear Dr. Fagni,

I am developing NailIQ for the 2026 Congressional App Challenge, a precautionary
nail-photo screener that reports visible findings without diagnosing systemic disease.
Your 2025 nail-psoriasis study is relevant to our work on onycholysis measurement.

Could a supervised research collaboration obtain deidentified original photographs,
anonymous patient/cohort grouping, individual pitting/crumbling/onycholysis assessments
and photo-adequacy flags? Do affected-area masks or separate leukonychia assessments
exist? We would also appreciate clarification of the cohort counts reported across the
abstract, tables and Results, and whether internal splits kept each patient together.

We would retain non-diagnosable images when reporting strict end-to-end performance.
Please clarify permitted training, annotations, aggregate publication and distribution
of resulting weights, including any restrictions on future public app use. Original
photographs would not be redistributed without explicit permission.

Thank you for considering this inquiry.

Source: [paper](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2025.1574413/full),
[contact in corrigendum](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2025.1617441/full).
Availability is a request lead; masks, leukonychia labels and reuse rights are unconfirmed.

## Lindsay's study draft

To: Jacek C. Szepietowski, jacek.szepietowski@pwr.edu.pl

Subject: Research inquiry about photographs from your half-and-half nail study

Dear Professor Szepietowski,

I am developing NailIQ for the 2026 Congressional App Challenge. It reports visible
nail findings without diagnosing underlying disease. Your 2026 half-and-half nail
study is relevant to our work on the proximal/distal color pattern.

Does the study retain original nail photographs with clinician assessments? If so,
could you clarify how many patients were photographed, how many had confirmed
half-and-half nails, and whether deidentified images and assessments could be shared
for a supervised research pilot?

Anonymous patient grouping, nail/view identifiers, uncertain assessments and capture
metadata would help keep evaluation independent. Please clarify permitted training,
derived annotations, aggregate publication, distribution of trained weights and any
restrictions on future public app use. We would not redistribute original images
without explicit permission.

Thank you for considering this request.

Source: [publisher](https://onlinelibrary.wiley.com/doi/10.1111/ijd.70302).
The reported 104-patient cohort is not a verified 104-positive-photo dataset.

## Weill Cornell draft

To: Shari Lipner, shl9032@med.cornell.edu

Subject: Research collaboration inquiry: visible longitudinal nail pigmentation

Dear Dr. Lipner,

I am developing NailIQ for the 2026 Congressional App Challenge, a precautionary
screener for visible nail findings. Your longitudinal-melanonychia cohort is relevant
to our work on recognizing a visible pigmented band across skin tones.

Does the cohort retain ordinary clinical photographs, separately from dermoscopic
images, that could be shared deidentified for a supervised research collaboration?
Could you clarify available photo and patient counts, repeat visits, anonymous grouping
keys, band annotations, uncertain assessments and capture metadata?

The proposed target is the visible nail sign; we are not proposing to classify melanoma
from this benign cohort. Please clarify permitted training, annotations, aggregate
publication, trained-weight distribution and any restrictions on future public app use.
Original images would not be redistributed without permission.

Thank you for considering this inquiry.

Source: [PubMed paper record](https://pubmed.ncbi.nlm.nih.gov/35752275/).
Photo inventory and sharing rights remain unconfirmed.

## Lam lab draft

To: Wilbur Lam, wilbur.lam@emory.edu

Subject: Research collaboration inquiry: fingernail images and retained quality-control cases

Dear Dr. Lam,

I am developing NailIQ for the 2026 Congressional App Challenge, a precautionary
nail-photo screener. Your fingernail-image work motivates a supervised study of capture
conditions and visible pallor, with clinical sign labels kept separate from anemia status.

Would a collaboration be possible using deidentified original fingernail images with
anonymous patient grouping and available hemoglobin reference/capture metadata? Were
images excluded for leukonychia, flash reflection, injury or other quality issues
retained? Those cases could help us test robustness without assuming a visible sign
from hemoglobin status alone.

We would welcome guidance on qualified sign review and on permitted training,
annotations, aggregate publication, trained-weight distribution and future public app
use. We would not redistribute the original images without explicit permission.

Thank you for considering this inquiry.

Sources: [study](https://www.nature.com/articles/s41467-018-07262-2),
[verified institutional contact](https://winshipcancer.emory.edu/profiles/lam-wilbur.php).
Access and retention of excluded images are unconfirmed.

## UNSM follow-up draft

To: Jorge Raul Navarro-Cabrera, jnavarroc@unsm.edu.pe

Subject: Follow-up: research access inquiry for your nail-image anemia study

Dear Dr. Navarro-Cabrera,

I am following up on my September 17 inquiry about research access to the nail images
from your 2025 study. NailIQ is my 2026 Congressional App Challenge project and reports
visible nail findings without diagnosing anemia or other underlying diseases.

Could you let me know whether a supervised research collaboration could obtain
deidentified original images, anonymous participant grouping, capture metadata,
photo-adequacy exclusions and hemoglobin reference measurements? Please identify
which reference measurements came from the Rad-67 device and whether any laboratory
reference or independent visible-pallor assessments are available.

We would also appreciate clarification of terms for training, annotations, aggregate
publication, resulting-weight distribution and future public app use. We would not
redistribute original photographs without explicit permission.

Thank you for your time.

Source: [paper](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2025.1557600/full).
Prior request is recorded in the canonical vault; reply status has not been checked
against email in this round. This draft has not been sent.

Balearic private-company images are excluded from the request shortlist; the published
code does not establish access or redistribution rights for the images.
