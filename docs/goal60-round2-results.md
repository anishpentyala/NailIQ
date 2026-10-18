# NailIQ round-two development results

**All-14 goal achieved: No.**

Completed October 3, 2026 under the October 2 approved protocol. Current VALID endpoint evidence: 1350 full source images, including 311 healthy images. Before-policy diagnostics meet the observed 60% recall / <=5% healthy-FP target for 12/14 signs; shown findings for 6/14. These are development results, not new independent clinical confirmation.

All positive abstentions and missing findings count as misses. FP uses all healthy images; healthy correct and abstention rates are reported separately. No historical TEST was selected or evaluated this round. Production weights and policy safeguards remain unchanged.

Minority-class counts remain small: melanonychia3, leukonychia11, Lindsay6 and onycholysis11 development positives. Their point estimates are provisional. Source/community labels and simulated framing do not establish patient-independent phone or clinical accuracy.

| Sign | Baseline recall | Selected recall before policy | Healthy FP | Shown recall | Selected route/model |
|---|---:|---:|---:|---:|---|
| Beau's lines | 76.5% (39/51) | 76.5% (39/51) | 0.0% (0/311) | 76.5% (39/51) | legacy / baseline |
| Clubbing appearance | 46.2% (37/80) | 75.0% (60/80) | 0.0% (0/311) | 0.0% (0/80) | detector_fallback / baseline |
| Cyanosis | 80.0% (52/65) | 80.0% (52/65) | 0.3% (1/311) | 80.0% (52/65) | legacy / baseline |
| Spoon-nail appearance | 43.5% (47/108) | 66.7% (72/108) | 0.3% (1/311) | 0.0% (0/108) | detector_fallback / baseline |
| Leukonychia | 72.7% (8/11) | 81.8% (9/11) | 0.6% (2/311) | 0.0% (0/11) | detector_fallback / baseline |
| Lindsay's nails | 0.0% (0/6) | 0.0% (0/6) | 0.0% (0/311) | 0.0% (0/6) | legacy / baseline |
| Melanonychia | 100.0% (3/3) | 100.0% (3/3) | 0.0% (0/311) | 0.0% (0/3) | legacy / baseline |
| Muehrcke's lines | 72.2% (26/36) | 72.2% (26/36) | 0.3% (1/311) | 72.2% (26/36) | legacy / baseline |
| Onychogryphosis | 89.2% (58/65) | 89.2% (58/65) | 0.0% (0/311) | 89.2% (58/65) | legacy / baseline |
| Onycholysis | 0.0% (0/11) | 0.0% (0/11) | 0.0% (0/311) | 0.0% (0/11) | legacy / baseline |
| Pallor proxy | 39.6% (134/338) | 72.2% (244/338) | 4.5% (14/311) | 0.0% (0/338) | legacy / pallor |
| Pitting | 77.0% (47/61) | 77.0% (47/61) | 0.3% (1/311) | 77.0% (47/61) | legacy / baseline |
| Splinter hemorrhages | 79.6% (39/49) | 79.6% (39/49) | 1.0% (3/311) | 79.6% (39/49) | legacy / baseline |
| Terry's nails | 81.9% (127/155) | 92.3% (143/155) | 1.6% (5/311) | 32.3% (50/155) | detector_fallback / ensemble |

| Sign | Positive abstentions | Healthy correct | Healthy abstentions | Recall 95% interval |
|---|---:|---:|---:|---:|
| Beau's lines | 3.9% (2/51) | 95.8% (298/311) | 4.2% (13/311) | 63.2%–86.0% |
| Clubbing appearance | 13.8% (11/80) | 85.2% (265/311) | 14.8% (46/311) | 64.5%–83.2% |
| Cyanosis | 7.7% (5/65) | 88.4% (275/311) | 11.3% (35/311) | 68.7%–87.9% |
| Spoon-nail appearance | 31.5% (34/108) | 84.9% (264/311) | 14.8% (46/311) | 57.3%–74.8% |
| Leukonychia | 18.2% (2/11) | 41.5% (129/311) | 57.9% (180/311) | 52.3%–94.9% |
| Lindsay's nails | 83.3% (5/6) | 95.2% (296/311) | 4.8% (15/311) | 0.0%–39.0% |
| Melanonychia | 0.0% (0/3) | 96.5% (300/311) | 3.5% (11/311) | 43.9%–100.0% |
| Muehrcke's lines | 5.6% (2/36) | 96.1% (299/311) | 3.5% (11/311) | 56.0%–84.2% |
| Onychogryphosis | 10.8% (7/65) | 76.8% (239/311) | 23.2% (72/311) | 79.4%–94.7% |
| Onycholysis | 63.6% (7/11) | 91.6% (285/311) | 8.4% (26/311) | 0.0%–25.9% |
| Pallor proxy | 3.8% (13/338) | 92.0% (286/311) | 3.5% (11/311) | 67.2%–76.7% |
| Pitting | 13.1% (8/61) | 80.1% (249/311) | 19.6% (61/311) | 65.1%–85.8% |
| Splinter hemorrhages | 12.2% (6/49) | 92.0% (286/311) | 7.1% (22/311) | 66.4%–88.5% |
| Terry's nails | 1.9% (3/155) | 97.4% (303/311) | 1.0% (3/311) | 87.0%–95.5% |

## What changed and what was rejected

- Clubbing appearance: selected `{"model": "baseline", "route": "detector_fallback"}`. Recall 46.2% → 75.0%; healthy FP 0.0% → 0.0%.
- Spoon-nail appearance: selected `{"model": "baseline", "route": "detector_fallback"}`. Recall 43.5% → 66.7%; healthy FP 0.0% → 0.3%.
- Leukonychia: selected `{"model": "baseline", "route": "detector_fallback"}`. Recall 72.7% → 81.8%; healthy FP 0.3% → 0.6%.
- Pallor proxy: selected `{"model": "pallor", "route": "legacy", "rules": [0.25, null, 0.05]}`. Recall 39.6% → 72.2%; healthy FP 4.8% → 4.5%.
- Terry's nails: selected `{"model": "ensemble", "route": "detector_fallback", "rules": [0.45, 0.15, null]}`. Recall 81.9% → 92.3%; healthy FP 2.6% → 1.6%.
- Six previously passing signs remain frozen EfficientNet/legacy. Detector-first fallback uses the complete legacy branch only for pre-policy failure/inconclusive; policy withholding cannot trigger fallback.
- Candidates violating FP or healthy-coverage limits were rejected. Extra healthy abstention may not exceed FP reduction+2 percentage points against the common baseline. Terry development FP cap is3%.
- Reliable side geometry remains authoritative. Top-photo shape findings carry no angle/depth. Clinical full images with simulated framing do not validate paired side measurements.
- Low-sample disagreement guards remain. Offline Lindsay zone and onycholysis area measurements have synthetic tests but no newly adjudicated clinical evidence; they were not integrated.

The new detector ROI has not been cleared by the existing display policy. Terry shown recall falls to32.3% (50/155), despite92.3% before-policy recall. Appearance, pallor and other unsupported findings stay withheld. This is a research candidate, not a deployable improvement to user-visible performance. No policy was relaxed to make the numbers pass.

## Verification and training lineage

- Endpoint/replay: 18900 findings, 0 shown/pre-policy/route mismatches. Frozen-v3 baseline regression: 0 mismatches. All per-sign coverage constraints pass.
- CPU/GPU regression: 64 frames, 896 findings, 0 exact verdict/route mismatches. Maximum rounded-probability difference 0.000000; maximum normalized-bbox difference 0.00000044. This is bounded device regression, not a full CPU population benchmark.
- Healthy-phone regression: one existing subject, four modes on each device; 0 device mismatches. Shown/pre-policy zero-false-alarm gates: True/True. Assisted boxes were reviewer selected.
- Pallor specialist: EfficientNet, seed42, 15/20 maximum epochs with early stopping. Best crop macro recall 84.9%; temperature1.0074. TRAIN Ghana healthy1383/pallor2050; crop VALID healthy186/pallor233. Four ambiguous `Anmeic` crop labels are excluded from the frozen full-image label parser; Ghana endpoint positives229. Labels are anemia proxies, not independent visible-pallor judgments.
- Exact input hashes, source counts and initializer records are retained. Initialization descends from earlier candidates; source matching applies to this fine-tuning stage, not all weight ancestry. Patient independence remains unproven.
- ML/backend236 tests pass. Frontend lint and build pass. Earlier partial CPU runs stopped during code review were discarded. The isolated GPU environment and disabled TF32 are recorded in cache metadata.
- Freeze binds models by model ID, manifests, weights, lineage, cache, parity and verification (verification SHA256 `162f86259ef3c2952431e063d78c7b39389e003dbecc6a8957b85f7d09dfceba`). It is experimental and deployment is not approved.

## Healthy scans and source breakdown

- pre_policy: any outside 24/311 (7.7%); all within 85/311; any inconclusive 222/311.
- shown: any outside 6/311 (1.9%); all within 0/311; any inconclusive 311/311.

| Source | Pallor caught | Healthy pallor FP | Terry caught | Healthy Terry FP |
|---|---:|---:|---:|---:|
| anemia-nails-detection | 82.6% (90/109) | unmeasured (0/0) | unmeasured (0/0) | unmeasured (0/0) |
| fingernails-ghana-anemia | 67.2% (154/229) | 6.5% (12/186) | unmeasured (0/0) | 0.0% (0/186) |
| nail-dataset-arthitaya | unmeasured (0/0) | 0.0% (0/13) | 100.0% (8/8) | 0.0% (0/13) |
| nail-disease-classification-nihati | unmeasured (0/0) | 4.0% (1/25) | 100.0% (4/4) | 0.0% (0/25) |
| nail-disease-detection-mxoqy | unmeasured (0/0) | 1.9% (1/54) | 87.5% (70/80) | 3.7% (2/54) |
| yolov8-nails-segmentation-ckvkd | unmeasured (0/0) | 0.0% (0/33) | 96.8% (61/63) | 9.1% (3/33) |

## Remaining dependency and artifacts

The local annotation index covers9998 TRAIN/VALID images with zero new clinical labels. Repeated photos are not independent patients. Five corrected access drafts are unsent. No clinician is arranged or new dataset acquired. Arrange qualified sign adjudication, grouping and permitted fresh paired-phone collection before asserting improved clinical performance. Planning targets150 positive patients/sign and400 healthy are not performance guarantees.

- [Clinical packets and unsent requests](goal60-round2-clinical-packet.md)
- [Approved protocol](goal60-round2-protocol.md)
- Development/selection: `ml/eval/goal60_round2_development_gpu_valid.*`, `data/raw/goal60_round2/selected_gpu.selection.json`
- Accepted endpoint/parity: `ml/eval/goal60_round2_selected_gpu_valid.*`, `ml/eval/goal60_round2_selected_verification.json`
- Device/phone: `ml/eval/goal60_round2_device_parity.*`, `ml/eval/goal60_round2_phone_parity.json`
- Frozen candidate: `data/raw/goal60_round2_frozen/routing.json` and `lineage.json`
- Review packets: `data/raw/goal60_round2_review`; specialist: `data/raw/goal60_round2_pallor`
