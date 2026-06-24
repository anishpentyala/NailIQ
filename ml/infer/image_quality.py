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
