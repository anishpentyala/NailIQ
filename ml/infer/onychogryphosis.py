"""Onychogryphosis (a thickened, overgrown, curved "ram's horn" nail) -- color track,
top-down photo, AI-only.

Unlike every other color condition there is no classical measurement here: nail
thickness and curvature don't show up as a color or texture pattern that a pixel
threshold could pick out. The verdict comes entirely from the color-condition CNN
(color_fusion.CNN_ONLY_CONDITIONS), which already trained on this class. This module
only supplies the finding's shape; when the CNN isn't available its answer is
"couldn't analyze", never a default "within".
"""

LABEL = "onychogryphosis"
DISPLAY_NAME = "Nail thickening (onychogryphosis)"


def inconclusive_finding(failure_reason):
    return {
        "label": LABEL,
        "display_name": DISPLAY_NAME,
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }


def build_finding(region):
    return inconclusive_finding("requires_ai_model")
