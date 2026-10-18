# Training-average repair — October 4, 2026

Fix: bootstrap the moving average from the first optimized state, then use decay
min(0.999, (1 + update_count) / (10 + update_count)). Preserve all other optimizer,
augmentation, floating-buffer averaging, learning-rate, selection and patience
settings. The legacy option remains available for reproduction. No inference or
display policy changes.

The previous saved Terry seed42 checkpoint had 17 updates; pallor seeds42/1337
had 15. Fixed decay0.999 retained 98.31%/98.51% of initialization, respectively.
Terry seed1337 had340 updates and retained71.16%. These are algebraic weights of
the initial state, not a claim about prediction accuracy or causal effect size.

One fixed experiment: `data/raw/goal60_image_round6_ema_repair`, exactly the round5
patient-family/image/crop-grouped TRAIN-derived fit, calibration and omitted
inventories, seeds42/1337, EfficientNet-B0, maximum20 epochs, batch64, patience6,
ImageNet initialization. Compare manifest hashes before starting. No prior NailIQ
weights, historical VALID/TEST training, new threshold sweep, or selected-seed
cherry-picking. Preserve old weights, scores, locks and pre-edit source.

Fit bounded two-view temperature and zero-added-negative cutoff on TRAIN-derived
calibration only, then freeze code/models/cutoffs before one reused VALID
diagnostic. Count localization/quality failures and abstentions as positive
misses. Report all14 signs, per-sign new healthy flags, scan union and omissions.
Protect prior correct positives and all six passing signs. A single new healthy
per-sign flag rejects the combined candidate, even if the scan union is unchanged.

Reused VALID and approximate patient grouping remain development evidence.
Community Terry labels and Hb/anemia pallor proxies are not qualified visible-sign
labels. No clinical grants, release, or evidence of phone-population accuracy can
come from this repair. Requests for existing qualified data remain unsent.

Verify the averaging bug with deterministic state tests, backend/inference tests,
endpoint/crop parity, CPU/GPU parity and the retained healthy-phone/stress checks.

Execution optimization, before any new VALID result: unchanged first-stage verdicts
may be reused from the prior signed calibration evidence only when reference model,
inference code, split inventory and original image/label/group hashes match. Extract
every automatic crop and score every repaired verifier again. Every256th image must
also match fresh full first-stage inference and crop/quality extraction. Retain all
5,122 images and bind cache provenance and parity counts to the new evidence.
