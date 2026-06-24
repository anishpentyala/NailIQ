"""Leukonychia (white discoloration of the nail plate) -- color track, top-down photo.

Classical CV like the geometry conditions: from the nail region (nail_region.py)
we measure the fraction of pixels that read as white discoloration, and flag an
unusually large white area as outside typical range. No trained model needed.
"""

from .nail_region import heuristic_confidence

# A pixel counts as "white discoloration": high value, low saturation. The very
# brightest pixels are excluded as specular glare (a blown-out highlight on a wet
# or angled nail is a photo artifact, not a sign).
WHITE_V_MIN = 0.80
WHITE_S_MAX = 0.20
GLARE_V_MAX = 0.97

# Rough starting estimate -- no labeled photo dataset yet to calibrate against. A
# normal nail shows little true white away from the lunula (which sits at the base,
# largely outside this distal region); above this fraction is flagged.
LEUKONYCHIA_WHITE_FRAC_THRESHOLD = 0.12


def white_fraction(region):
    S, V = region["S"], region["V"]
    if V.size == 0:
        return 0.0
    white = (V > WHITE_V_MIN) & (S < WHITE_S_MAX) & (V <= GLARE_V_MAX)
    return float(white.mean())


def fraction_to_verdict(frac):
    return "outside" if frac > LEUKONYCHIA_WHITE_FRAC_THRESHOLD else "within"


def build_finding(region):
    frac = white_fraction(region)
    return {
        "label": "leukonychia",
        "display_name": "Nail color (leukonychia)",
        "value": None,
        "unit": None,
        "verdict": fraction_to_verdict(frac),
        "confidence": heuristic_confidence(frac, LEUKONYCHIA_WHITE_FRAC_THRESHOLD),
        "track_used": "color",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "leukonychia",
        "display_name": "Nail color (leukonychia)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "color",
        "failure_reason": failure_reason,
    }
