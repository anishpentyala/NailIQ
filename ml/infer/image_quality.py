"""Color-constancy, skin-tone, and photo-quality helpers for the color/texture track.

The color conditions (leukonychia, melanonychia, pallor, cyanosis, Terry's nails, …)
read *absolute* or *relative* color off the nail plate, which makes them hostage to
two things the geometry track never cared about:

  1. The phone's auto white balance. The same nail photographed under warm indoor
     light vs. cool daylight has very different raw RGB, so "is this nail pale/blue/
     white" is meaningless until the illuminant colour is normalised. `white_balance`
     applies Shades-of-Gray color constancy (Finlayson & Trezzi 2004, Minkowski
     p=6) before any color is measured.

  2. Skin tone. Several signs are tone-dependent: longitudinal melanonychia is
     common and usually benign in darker skin, and "pallor" must be judged relative
     to the person, not an absolute. `ita_degrees` computes the Individual Typology
     Angle (Chardon 1991), the standard objective skin-tone metric, from CIELab so
     conditions can adjust their thresholds rather than over-flag darker skin.

Plus simple gates so we don't measure color on an invalid photo at all: heavy
specular glare, or nail polish (which hides the real plate entirely).

Everything here is classical CV -- no trained model -- and the functions are pure
(operate on arrays/images) so they're unit-testable without a camera.
"""

import cv2
import numpy as np

# A pixel this bright is blown-out specular glare, not nail color.
GLARE_V = 0.97
# Above this fraction of the nail region being glare, color readings aren't trustworthy.
GLARE_FRAC_MAX = 0.25
# Natural nail/skin saturation is low; a plate this saturated over much of its area
# is almost certainly nail polish, which hides every color/texture sign.
POLISH_S = 0.45
POLISH_FRAC_MAX = 0.5


def white_balance(bgr, p=6):
    """Shades-of-Gray color constancy. Normalises the illuminant colour so absolute
    color findings don't swing with the camera's auto white balance. p=1 is plain
    Gray-World, p->inf approaches max-RGB; p=6 is the published sweet spot."""
    img = bgr.astype(np.float32)
    means = np.power(np.mean(np.power(img, p), axis=(0, 1)), 1.0 / p)  # per-channel
    gray = float(means.mean())
    scale = gray / (means + 1e-6)
    return np.clip(img * scale, 0, 255).astype(np.uint8)


def ita_degrees(L, b):
    """Individual Typology Angle (degrees) from CIELab L* (0..100) and b* (centered
    at 0) pixel arrays. Higher ITA = lighter skin (>41 very light, <28 tan/brown,
    <10 dark). Uses medians for robustness. Returns None if undefined."""
    if L.size == 0 or b.size == 0:
        return None
    Lm = float(np.median(L)) - 50.0
    bm = float(np.median(b))
    if abs(bm) < 1e-6:
        return None
    return float(np.degrees(np.arctan2(Lm, bm)))


def lab_real(bgr):
    """CIELab with L in 0..100 and a/b centered at 0 (OpenCV packs them 0..255)."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab).astype(np.float32)
    L = lab[..., 0] * 100.0 / 255.0
    a = lab[..., 1] - 128.0
    b = lab[..., 2] - 128.0
    return L, a, b


def glare_fraction(V):
    """Fraction of nail-region Value samples that are blown-out glare."""
    return float(np.mean(V > GLARE_V)) if V.size else 0.0


def polish_fraction(S):
    """Fraction of nail-region Saturation samples consistent with nail polish."""
    return float(np.mean(S > POLISH_S)) if S.size else 0.0


def quality_reason(V, S):
    """Return an inconclusive reason if the nail region is unfit for color analysis,
    else None. Glare and polish both make color readings meaningless."""
    if polish_fraction(S) > POLISH_FRAC_MAX:
        return "nail_polish_detected"
    if glare_fraction(V) > GLARE_FRAC_MAX:
        return "too_much_glare"
    return None


# --- Per-photo quality score (for the result screen) -------------------------
# Turns the raw signals above into one 0..100 number the UI can show. Like the
# rest of this track it's an *uncalibrated heuristic*, not a calibrated measure:
# the constants are reasonable starting points, not fit against a labelled set.

# Laplacian variance at/above which focus counts as full marks. focus_score()
# returns variance in the hundreds for a crisp phone macro; BLUR_THRESHOLD (20)
# is the floor below which the photo is rejected outright, so "good" sits well above it.
FOCUS_GOOD = 120.0
QUALITY_GOOD_MIN = 70  # score >= this -> "good"
QUALITY_FAIR_MIN = 40  # score >= this -> "fair", else "poor"


def photo_quality(focus, glare_frac=None, polish_frac=None):
    """0..100 photo-quality score + band + issue list, from already-computed signals.

    Weakest-link scoring: the worst of focus/glare/polish caps the score, since any
    one of them ruins the photo. glare_frac/polish_frac are None for the side photo
    (no nail-region colour sampling happens there), so it's scored on focus alone.
    """
    focus_c = float(np.clip(focus / FOCUS_GOOD, 0.0, 1.0))
    glare_c = 1.0 if glare_frac is None else float(np.clip(1.0 - glare_frac / GLARE_FRAC_MAX, 0.0, 1.0))
    polish_c = 1.0 if polish_frac is None else float(np.clip(1.0 - polish_frac / POLISH_FRAC_MAX, 0.0, 1.0))

    score = int(round(100 * min(focus_c, glare_c, polish_c)))

    issues = []
    if focus_c < 0.5:
        issues.append("blurry")
    if glare_c < 0.5:
        issues.append("glare")
    if polish_c < 0.5:
        issues.append("polish")

    band = "good" if score >= QUALITY_GOOD_MIN else "fair" if score >= QUALITY_FAIR_MIN else "poor"
    return {"score": score, "band": band, "issues": issues}
