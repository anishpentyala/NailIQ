# What we need from outside reviewers

The software workflow is ready. No new clinical labels or independent patient
photos have been supplied. Current results remain development measurements.

1. Arrange a qualified clinician to review visible nail signs. Record their
   qualification and a reviewer ID. Keep model predictions hidden during review.
2. Start with a development group to improve pallor and Terry's-nail detection.
   Record each of the fourteen signs as present, absent or indeterminate. Anemia
   diagnoses alone do not establish visible nail pallor. A healthy control needs
   all fourteen signs reviewed absent.
3. Retain each patient's first prescribed side and top photo pair, including poor
   captures. Record a patient-group ID, source, tone band, photo adequacy and the
   permitted-use reference. Avoid names in the evaluation files. Identify repeated
   patients and near-duplicate photos before splitting data.
4. Keep development and later confirmation patients separate. Explicitly assign
   development patients to TRAIN or VALID before preparing specialist training
   crops. The existing software checks exact duplicates and recorded groups;
   reviewers must confirm actual patient independence.
5. Improve the routes on development data, repeat the shared false-alarm checks,
   and freeze the final models, rules and proposed permissions. The present
   ten-target simulation is not ready for twelve-target confirmation.
6. Only then collect a separate confirmation group. Current evidence-gate defaults
   are 150 independently reviewed positive patients per claimed sign and 400
   healthy patients. Exact crop branches and source/tone groups may need more.
   These numbers are planning gates, not a guarantee or power calculation.

The empty development and confirmation forms are in
`data/raw/goal60_withholding_round3/*-cohort.template.json`. They contain no patient
records. The earlier 9,998-image review index is for development triage; its source
labels are not newly reviewed clinical findings. Five existing access-request
drafts remain unsent.

[Implementation protocol](goal60-withholding-protocol.md) explains the locked,
one-use confirmation and grant requirements. [Results](goal60-withholding-results.md)
separates displayed results from simulated approvals.
