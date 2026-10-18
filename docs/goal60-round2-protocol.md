# Round two: local development protocol

Approved October 2, 2026. Two-photo capture remains; no clinician is arranged.
Historical TEST is excluded from this round. No production deployment is approved.

Common baseline: frozen v3 EfficientNet/legacy, unchanged weights/rules and v3 exclusions.
Fixed alternatives: legacy, detector, detector with complete legacy fallback only on
pre-policy inconclusive/failure. Explicit assisted boxes override all automatic routes.
Flat/blurry global failures cannot be rescued. Geometry remains authoritative.

All candidates share the same VALID files/labels. Per-sign extra healthy abstention may
not exceed healthy FP reduction plus 0.02. With FP<=0.05, maximize strict recall, then
fewer FP, higher healthy correct rate and simpler configuration. Retain baseline absent
an improvement. The six passing signs stay on baseline. Terry uses the existing grid,
development FP<=0.03 and recall>=0.60. Existing policies/disagreement guards remain.

One pallor specialist: EfficientNet, 20 epochs maximum with existing early stopping,
batch16, workers2, macro-recall crop checkpoint selection, source-matched TRAIN/VALID,
v3 exclusions, label-aligned warm start from frozen v3. No TEST evaluation. These are
anemia-proxy labels, not clinician-adjudicated visible pallor. Initialization ancestry
includes earlier candidates; source matching applies to this fine-tuning stage only.

Cache complete branch evidence and fingerprint models, locator, rules, code, exclusion
and ordered source-image/label hashes. Require zero endpoint/replay mismatches across
all14. Report both pre-policy and shown findings, all abstentions, healthy correct rate,
source breakdown and directly measured scan-level FP. Phone checks cover one existing
healthy subject in four modes and cannot establish population accuracy.

Prepare TRAIN/VALID-only annotation packets and draft clinical data requests. Clinical
labels stay unassessed pending a qualified reviewer; data access and fresh confirmation
are external dependencies. Keep failed experiments and update canonical vault records.
