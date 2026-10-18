"""Turn on the top-photo appearance route for koilonychia in the color-CNN manifest.

When the side-profile geometry measurement is unusable (usually, on phone photos: see
measurement_gate.py), ml/infer/appearance.py can answer koilonychia from the color CNN's read of the
top photo. The route stays off until the manifest (ml/models/nail_color_classifier_labels.json, gitignored)
lists the sign, which this script does, with the rule picked by ml/eval/tune_color_decision.py on VALID.

Evidence (2026-10-17, ml/eval/eval_end_to_end.py --include-shapes --include-authorized, rule floor 0.1):
  koilonychia valid 78.0% recall / 2.2% healthy FP (n=109 / 318); test 70.8% / 3.8% (n=72 / 240).
  Per source on TEST: KNM 79%, chaa 64%, NIHATI 2/2; healthy false alarms chaa 11% (6/54), others ~3%.
clubbing does NOT clear the bar through this route (valid 43.8%, test 50.0%), so it is not enabled.

Run from repo root: ml/venv/Scripts/python.exe scripts/enable_appearance_route.py
"""
import json
from pathlib import Path

MANIFEST = Path("ml/models/nail_color_classifier_labels.json")
# floor 0.3 (2026-10-18 FP reduction): valid 58.7% / 1.3% FP, test 63.9% / 1.7% (was floor 0.1: 78.0%/2.2%, 70.8%/3.8%)
ENABLE = {"koilonychia": {"floor": 0.3}}


def main():
    meta = json.loads(MANIFEST.read_text())
    meta["appearance_conditions"] = sorted(ENABLE)
    meta["appearance_rules"] = ENABLE
    meta["validated_appearance_conditions"] = sorted(ENABLE)
    meta["validated_roi_modes"] = ["legacy"]  # the mode every end-to-end number above was measured in
    MANIFEST.write_text(json.dumps(meta, indent=2))
    print("appearance route enabled for", sorted(ENABLE))


if __name__ == "__main__":
    main()
