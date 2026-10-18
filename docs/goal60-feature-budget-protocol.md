# Feature budget diagnostics — October 4, 2026

Added after seeing the first zero-false-alarm TRAIN calibration results, before
any successful VALID scoring. Those calibration recalls were below 1%, so explicitly
measure the tradeoff rather than describe threshold changes as a solution.

Use the same frozen feature/model candidates. For each sign and TRAIN-calibration
healthy-FP budget of 0%, 1%, 3%, 5%, choose a threshold and depth by TRAIN calibration
only. Freeze all eight choices and harness hash before VALID evaluation. Report every
option, never select/retrain using VALID or consume historical TEST.

These budgets are diagnostics, not permission to increase displayed false alarms.
A rescue adds positive calls only; zero newly flagged healthy images remains required
for strict preservation. Report cases where recall rises at the cost of healthy flags.
No option can issue a clinical grant or validate anemia proxies as visible pallor.
