# NailIQ all-14 candidate results

**Target achieved:** No.

Selected experiment: **EfficientNet / legacy**, using the fixed VALID-only selection protocol.
Final TEST pre-policy diagnostic: 6/14 signs meet recall >=60% and healthy FP <=5%.
This diagnostic is before withholding unsupported findings. It is not deployed performance.

All inconclusive positives and absent findings count as misses. Healthy false positives use every
healthy image; the separate healthy correct rate also counts abstentions as failures.
The benchmark uses source-dataset labels and simulated framing. It does not validate diagnoses,
side-profile measurements or real phone performance. Shape rows concern top-photo appearance only.

| Sign | Frozen VALID recall before policy | TEST recall before policy | TEST healthy FP before policy | TEST shown recall |
|---|---:|---:|---:|---:|
| Clubbing appearance | 46.2% (37/80) | 59.6% (31/52) | 0.00% (0/239) | 0.0% (0/52) |
| Spoon-nail appearance | 43.5% (47/108) | 42.0% (29/69) | 0.00% (0/239) | 0.0% (0/69) |
| Leukonychia † | 72.7% (8/11) | 40.0% (4/10) | 1.26% (3/239) | 0.0% (0/10) |
| Melanonychia † | 100.0% (3/3) | 50.0% (3/6) | 0.00% (0/239) | 0.0% (0/6) |
| Pallor | 39.6% (134/338) | 26.1% (95/364) | 5.02% (12/239) | 0.0% (0/364) |
| Cyanosis | 80.0% (52/65) | 90.3% (28/31) | 1.26% (3/239) | 90.3% (28/31) |
| Terry's nails | 81.9% (127/155) | 76.9% (70/91) | 5.02% (12/239) | 76.9% (70/91) |
| Lindsay's nails † | 0.0% (0/6) | 0.0% (0/5) | 0.00% (0/239) | 0.0% (0/5) |
| Onycholysis † | 0.0% (0/11) | 0.0% (0/15) | 0.00% (0/239) | 0.0% (0/15) |
| Beau's lines | 76.5% (39/51) | 78.8% (26/33) | 0.00% (0/239) | 78.8% (26/33) |
| Muehrcke's lines † | 72.2% (26/36) | 72.2% (13/18) | 0.42% (1/239) | 72.2% (13/18) |
| Splinter hemorrhages | 79.6% (39/49) | 88.2% (45/51) | 0.00% (0/239) | 88.2% (45/51) |
| Pitting | 77.0% (47/61) | 65.6% (21/32) | 0.42% (1/239) | 65.6% (21/32) |
| Onychogryphosis | 89.2% (58/65) | 79.4% (27/34) | 0.00% (0/239) | 79.4% (27/34) |

† Fewer than 30 TEST positives: provisional and particularly sensitive to individual photos.

Terry's nails exceeds the healthy false-positive limit: 12/239 = 5.02%, not a rounded 5% pass.

| Sign | TEST recall 95% interval before policy | Healthy correct rate before policy | Balanced accuracy before policy | Positive abstentions before policy | Healthy abstentions before policy |
|---|---:|---:|---:|---:|---:|
| Clubbing appearance | 46.1%–71.8% | 64.9% (155/239) | 62.2% | 34.6% (18/52) | 35.1% (84/239) |
| Spoon-nail appearance | 31.1%–53.8% | 64.9% (155/239) | 53.4% | 53.6% (37/69) | 35.1% (84/239) |
| Leukonychia | 16.8%–68.7% | 50.6% (121/239) | 45.3% | 60.0% (6/10) | 48.1% (115/239) |
| Melanonychia | 18.8%–81.2% | 98.3% (235/239) | 74.2% | 0.0% (0/6) | 1.7% (4/239) |
| Pallor | 21.9%–30.8% | 93.3% (223/239) | 59.7% | 3.6% (13/364) | 1.7% (4/239) |
| Cyanosis | 75.1%–96.7% | 83.3% (199/239) | 86.8% | 6.5% (2/31) | 15.5% (37/239) |
| Terry's nails | 67.3%–84.4% | 92.1% (220/239) | 84.5% | 6.6% (6/91) | 2.9% (7/239) |
| Lindsay's nails | 0.0%–43.4% | 96.2% (230/239) | 48.1% | 100.0% (5/5) | 3.8% (9/239) |
| Onycholysis | 0.0%–20.4% | 86.6% (207/239) | 43.3% | 80.0% (12/15) | 13.4% (32/239) |
| Beau's lines | 62.2%–89.3% | 98.3% (235/239) | 88.6% | 3.0% (1/33) | 1.7% (4/239) |
| Muehrcke's lines | 49.1%–87.5% | 97.9% (234/239) | 85.1% | 5.6% (1/18) | 1.7% (4/239) |
| Splinter hemorrhages | 76.6%–94.5% | 97.1% (232/239) | 92.7% | 3.9% (2/51) | 2.9% (7/239) |
| Pitting | 48.3%–79.6% | 74.1% (177/239) | 69.8% | 15.6% (5/32) | 25.5% (61/239) |
| Onychogryphosis | 63.2%–89.7% | 67.8% (162/239) | 73.6% | 17.6% (6/34) | 32.2% (77/239) |

Candidate comparisons are pre-policy VALID diagnostics, not deployment approvals:

| Automatic experiment | Signs passing both limits on VALID | Mean recall under FP cap | Mean healthy correct rate |
|---|---:|---:|---:|
| EfficientNet / legacy | 9/14 | 61.3% | 84.7% |
| Ensemble / legacy | 9/14 | 61.1% | 84.8% |
| Ensemble / detector | 8/14 | 49.4% | 70.0% |
| EfficientNet / detector | 7/14 | 48.9% | 71.2% |
| MobileNet / legacy | 6/14 | 50.2% | 83.5% |
| MobileNet / detector | 4/14 | 46.6% | 67.1% |

Healthy phone regression: **passed**, 1 existing subject; raw, guide-cropped and reviewer-assisted modes.
The assisted boxes were reviewer-selected; this is not a user study or population benchmark.
Production weights and existing validation/low-sample safeguards remain unchanged.

The nail locator reached 91.3% box recall and 83.0% box precision on VALID at IoU >=0.5.
Its first endpoint run regressed because focus was measured on a smooth tight interior rather
than the classifier crop. The correction uses the same 15% padded crop and the unchanged focus
threshold: 41/60 previously rejected VALID photos cleared it; 0/60 synthetically blurred versions did.
Old failed runs are preserved. Annotation-box runs remain oracle diagnostics excluded from selection.

A VALID-only guard audit found zero positive classical measurements for Lindsay's nails (0/6)
and onycholysis (0/11) across legacy, detector and annotation-box routes. With the retained
low-sample disagreement guard, no CNN-only retrain can produce a positive call on those same
examples. Recovering them requires better validated measurements and independent evidence,
rather than a lower CNN threshold. Audit: ml/eval/goal60_guard_recall_ceiling_valid.json.

V3 quarantine excludes 73 crops, including three newly confirmed duplicate pairs. Known linked
source families were excluded; complete cross-source patient/near-duplicate independence is not proven.
Compatible initialization weights came from earlier isolated candidates; training was not from scratch.
KNM and Arthitaya were included under explicit user-reported permission, without relabeling the Unknown
public Arthitaya license. Runtime crops are additional views, not new independent subjects.

Evidence artifacts:

- [Frozen VALID](<C:/Users/Anish/OneDrive - Lake Washington School District/Desktop/Projects/CAC 2026 Nail Health App/ml/eval/goal60_final_frozen_valid.json>)
- [Final TEST](<C:/Users/Anish/OneDrive - Lake Washington School District/Desktop/Projects/CAC 2026 Nail Health App/ml/eval/goal60_final_frozen_test.json>)
- [Selection and per-source metrics](<C:/Users/Anish/OneDrive - Lake Washington School District/Desktop/Projects/CAC 2026 Nail Health App/ml/eval/goal60_final_selection.json>)
- [Phone regression](<C:/Users/Anish/OneDrive - Lake Washington School District/Desktop/Projects/CAC 2026 Nail Health App/ml/eval/goal60_final_frozen_phone.json>)

Across all 14 findings, the final TEST healthy-label scan has:

- Any pre-policy outside finding: 12.6% (30/239).
- Any shown outside finding: 6.3% (15/239).
- All 14 pre-policy findings within: 38.5% (92/239).
- Any pre-policy inconclusive finding: 60.3% (144/239).
These scan-level rates differ from each condition's false-positive rate; abstention is not a correct healthy call.

![All-14 TEST recall and uncertainty](<C:/Users/Anish/OneDrive - Lake Washington School District/Desktop/Projects/CAC 2026 Nail Health App/docs/goal60-test-recall.png>)
