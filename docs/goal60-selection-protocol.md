# Fixed candidate selection and final evaluation

Recorded before the new detector and ensemble endpoint results. The target is
strict detection recall >=60% for each of all 14 signs, with <=5% false positives
among all healthy images. Abstentions and missing findings count as misses; healthy
abstentions also reduce the reported healthy correct rate. This is a dataset
screening benchmark, not clinical diagnostic accuracy.

Compare the frozen authorized MobileNet, EfficientNet and equal-weight ensemble using
automatic legacy localization and the new nail detector. Ground-truth annotation
boxes are localization diagnostics and cannot win selection. Keep the original
source splits and v3 duplicate quarantine. Thresholds are selected only on VALID
using the production fusion functions, with replay parity required and the tuner's
existing healthy-abstention constraint retained.

Rank these experiments by the number of all 14 pre-policy signs reaching both
limits, then mean strict recall (score zero for a sign exceeding the FP limit),
then mean healthy correct rate. Prefer fewer model members and legacy localization
if otherwise tied. Pre-policy results are research diagnostics; existing withheld
conditions, low-sample guards and separate ROI/appearance approval gates remain
active. A candidate passing only some signs does not fulfill the goal.

Freeze the selected weights, locator, rules and VALID evidence hashes in a new
directory. Re-run VALID through `/analyze` with those actual frozen rules to check
the offline replay, then evaluate TEST without selecting or changing thresholds
from its results. Run the existing healthy phone subject in raw, guide-cropped and
reviewer-assisted modes. Any pre-policy false alarm fails that regression check;
one subject's clean result cannot establish population accuracy.

Report all 14 with shown and pre-policy recall, healthy false positives/correct
rate, abstentions, denominators and Wilson intervals. Melanonychia VALID3/TEST6,
Lindsay VALID6/TEST5 and other small pools remain provisional. Side geometry and
real phone performance require independent paired and labeled data. Do not replace
production weights if the complete target or the regression check fails; preserve
experimental artifacts and state the unmet conditions.
