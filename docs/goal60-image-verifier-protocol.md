# Published-label and image-verifier implementation

Goal: 12/14 displayed signs with strict recall >=60%, then all14. Preserve the
six currently passing signs, correct detections, coverage and the existing
4/311 healthy-scan flags. Failed positive images count as misses.

## Implemented workflow

1. Published expert-label importer accepts partial present/absent/indeterminate
   assessments with source, assessor, patient and rights references. Missing
   signs remain unknown. Original reviewer disagreements remain indeterminate,
   retaining every original assessment instead of manufacturing a consensus.
   Pallor explicitly requires visible-nail-sign assessment.
   Side-view availability never implies validated angle/depth measurements.
2. Separate published crop builder accepts development only, preassigned patient
   train/calibration/holdout roles and original photo bytes with automatic
   localization. No holdout crops enter training. Separate partial-label evaluator
   reports every sign's assessed and missing counts. The strict paired clinical
   importer and release gates remain unchanged. The separate
   mine_goal60_published_negatives.py ranks only explicitly assessed TRAIN negatives;
   it never opens calibration/holdout images. Execution awaits actual eligible labels.
3. Development alternative uses existing localized source crops. Connected known
   patient-family, exact-original and exact-crop groups remain together. Components
   touching historical VALID are quarantined from TRAIN. TRAIN groups are fixed
   into fit/calibration/omitted folds before training. Terry's CHAA source is
   entirely omitted from verifier fit/calibration. Fine-tuning sources must provide
   both target and negative labels. Unknown patient relationships remain a limitation.
4. EfficientNet-B0 replicas use seeds42 and1337, maximum20 epochs, existing macro
   recall checkpoint selection and ImageNet initialization. Existing NailIQ candidate
   initialization is avoided because it has already seen the omitted source.
   Calibrated replica probabilities are averaged. Original runs are preserved;
   finite temperature calibration matches horizontal-flip inference and minimizes
   calibration NLL over [.05,100]. A boundary fit is reported, not hidden.
5. First stage stays fixed: Terry ensemble detector_fallback [.45,.15,null];
   pallor earlier specialist legacy [.25,null,.05]. Verifier uses the automatically
   localized legacy nail crop and existing ROI-quality checks. Only a supported
   first-stage positive plus a verifier positive may propose an added positive.
   Otherwise the complete displayed reference finding stands. Actual app findings
   never change in this shadow workflow.
6. Threshold uses only TRAIN-derived calibration with zero extra target-negative
   positives and a .5 floor. An observed negative score1 disables additions.
   Models, evidence, code, reference and cutoffs are hashed before diagnostic VALID.
   Report raw first-stage, hypothetical additions, actual displayed findings,
   all14, protected signs, healthy scan union, coverage, sources, estimated tone,
   uncertainty and the omitted verifier cohorts separately.

## Available evidence and pending acquisition

Available Terry labels are community dataset labels. Available pallor labels are
anemia/Hb proxies, not independently assessed visible pallor. These runs cannot
authorize clinical display, even if a development point estimate passes.
Some existing negative cohorts use Hb-normal proxies; these do not establish
absence of Terry's nails or all14 signs. Healthy FP numbers refer to the inherited
development label benchmark, not clinically verified all-sign healthy patients.
The earlier first-stage models have seen original TRAIN sources: the newly omitted
cohorts are verifier-only holdouts, not independent full-pipeline confirmation.

[Nelson request](goal60-terry-data-request.md) and
[SEWA request](goal60-sewa-data-request.md) are prepared with verified public
recipients and await explicit send approval. SEWA contact sharing/agreement
acceptance separately awaits approval. No source has been acquired by drafting
or importing an empty template. Exact label vocabulary, assessor qualifications,
patient grouping, views and permitted model use must be audited upon receipt.

## Commands and rollback

Use scripts/prepare_goal60_image_verifiers.py, train_goal60_image_verifiers.py,
freeze_goal60_image_verifiers.py and evaluate_goal60_image_verifiers.py. New
published labels use build_goal60_published_specialist.py and
evaluate_published_sign_verifier.py. CPU and CUDA use the same frozen weights.

Experiment artifacts stay under data/raw/goal60_image_round5_verified. Earlier
round5 preparation is retained as superseded. Original unbounded calibration is
retained; only the separate calibrated bundle is eligible for research scoring.
No production model, public API, display policy or release permission is changed.
Rollback is to stop using the isolated experiment files; no production rollback
is needed. Fresh clinically eligible evidence remains required for display.
