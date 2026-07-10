"""Skin-tone coverage gating for the color/texture findings.

The color track's thresholds and the color CNN were fit/validated on data that
`ml/eval/audit_skin_tone.py` shows is heavily skewed toward light skin: of the
~430 dataset images where a skin region is even measurable, ~59% fall in the
lightest ITA band and the darker bands are thin and noisy. We therefore have
*little validation* of the color findings on darker skin tones.

Rather than fake a per-tone calibration we don't have the data for, this module
does the honest thing: classify each scan's skin tone (from the ITA already
computed in `nail_region`) into a coverage tier, and on under-represented tones
cap the color findings' confidence and attach a plain-English caveat the UI
surfaces. This matches the rest of the color track, which deliberately leans
conservative because its numbers are uncalibrated.

ITA (Individual Typology Angle): higher = lighter skin. Band edges are the
standard dermatology cut-points (see image_quality.ita_degrees).
"""

# ITA band edges in degrees, light -> dark. (name, lo_inclusive, hi_exclusive).
_BANDS = [
    ("very_light", 41.0, 1e9),
    ("light", 28.0, 41.0),
    ("intermediate", 19.0, 28.0),
    ("tan", 10.0, 19.0),
    ("brown", -30.0, 10.0),
    ("dark", -1e9, -30.0),
]

# Coverage tier per band, from the audit (ml/eval/audit_skin_tone.py). "well" =
# the lightest tones the data actually covers; "limited"/"minimal" = tones the
# color findings are largely unvalidated on. Re-derive these if the dataset grows.
_COVERAGE = {
    "very_light": "well",
    "light": "well",
    "intermediate": "limited",
    "tan": "limited",
    "brown": "minimal",
    "dark": "minimal",
}

# Confidence ceilings applied to a color finding when the tone is under-represented.
# Both sit below nail_region.heuristic_confidence's own 0.65 cap, on purpose.
_CONFIDENCE_CAP = {"limited": 0.50, "minimal": 0.40}

_CAVEAT = {
    "limited": "This skin tone is under-represented in our test data, so this "
               "color reading is less validated for you -- treat it as a weaker signal.",
    "minimal": "We have very little validation data for darker skin tones, so this "
               "color reading may be unreliable for you. Don't read much into it.",
}


def ita_band(skin_ita):
    """ITA degrees -> band name, or None when ITA couldn't be measured."""
    if skin_ita is None:
        return None
    for name, lo, hi in _BANDS:
        if lo <= skin_ita < hi:
            return name
    return None


def coverage_tier(band):
    """Band name -> 'well' | 'limited' | 'minimal'. 'well' when band is None
    (no tone measured -> nothing to flag, leave findings untouched)."""
    if band is None:
        return "well"
    return _COVERAGE.get(band, "well")


def skin_tone_summary(skin_ita):
    """Small dict for the /analyze response so the UI can show what was assessed."""
    band = ita_band(skin_ita)
    return {
        "ita": round(skin_ita, 1) if skin_ita is not None else None,
        "band": band,
        "coverage": coverage_tier(band),
    }


def apply_coverage(findings, skin_ita):
    """Dampen + annotate color findings on under-represented skin tones.

    On 'well' coverage (or unmeasurable tone) findings pass through unchanged. On
    'limited'/'minimal', each finding's confidence is capped and a `tone_caveat`
    (English, kept for any consumer that just wants prose) + a `tone_tier`
    ('limited' | 'minimal', a stable key the frontend maps through i18n the same
    way it does `label` -> `findingName()`) + `skin_tone_band` are attached.
    Returns the (mutated) findings list.
    """
    tier = coverage_tier(ita_band(skin_ita))
    if tier == "well":
        return findings
    cap = _CONFIDENCE_CAP[tier]
    caveat = _CAVEAT[tier]
    band = ita_band(skin_ita)
    for f in findings:
        if f.get("confidence") is not None:
            f["confidence"] = round(min(f["confidence"], cap), 2)
        f["tone_caveat"] = caveat
        f["tone_tier"] = tier
        f["skin_tone_band"] = band
    return findings
