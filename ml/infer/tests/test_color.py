import numpy as np

from ml.infer.leukonychia import fraction_to_verdict, white_fraction
from ml.infer.melanonychia import band_contrast, contrast_to_verdict, tone_adjusted_threshold
from ml.infer.nail_region import NAIL_WIDTH_FRAC, compute_nail_region


def _region(S, V, across):
    S, V, across = np.asarray(S, float), np.asarray(V, float), np.asarray(across, float)
    return {"S": S, "V": V, "across": across, "along": np.zeros_like(V),
            "region_px": V.size, "finger_px": V.size * 10}


# --- leukonychia ---------------------------------------------------------------

def test_leukonychia_pink_nail_is_within():
    n = 1000
    region = _region(S=np.full(n, 0.5), V=np.full(n, 0.6), across=np.zeros(n))
    assert white_fraction(region) == 0.0
    assert fraction_to_verdict(white_fraction(region)) == "within"


def test_leukonychia_large_white_area_is_outside():
    n = 1000
    S = np.full(n, 0.5); V = np.full(n, 0.6)
    S[:300] = 0.05; V[:300] = 0.9  # 30% white discoloration
    region = _region(S, V, across=np.zeros(n))
    assert white_fraction(region) > 0.12
    assert fraction_to_verdict(white_fraction(region)) == "outside"


def test_leukonychia_specular_glare_not_counted():
    # Blown-out highlights (V near 1.0) are photo artifacts, not leukonychia.
    n = 1000
    S = np.full(n, 0.5); V = np.full(n, 0.6)
    S[:300] = 0.0; V[:300] = 0.99
    region = _region(S, V, across=np.zeros(n))
    assert white_fraction(region) == 0.0
    assert fraction_to_verdict(white_fraction(region)) == "within"


# --- melanonychia --------------------------------------------------------------

def test_melanonychia_uniform_plate_is_within():
    n = 1100
    across = np.linspace(-NAIL_WIDTH_FRAC, NAIL_WIDTH_FRAC, n)
    region = _region(S=np.full(n, 0.4), V=np.full(n, 0.6), across=across)
    assert band_contrast(region) == 0.0
    assert contrast_to_verdict(band_contrast(region)) == "within"


def test_melanonychia_dark_central_band_is_outside():
    n = 1100
    across = np.linspace(-NAIL_WIDTH_FRAC, NAIL_WIDTH_FRAC, n)
    V = np.full(n, 0.6)
    V[np.abs(across) < 0.06] = 0.2  # dark stripe down the middle
    region = _region(S=np.full(n, 0.4), V=V, across=across)
    assert band_contrast(region) > 0.40
    assert contrast_to_verdict(band_contrast(region)) == "outside"


def test_melanonychia_dark_skin_needs_stronger_band():
    # A moderate band that trips the default threshold should NOT flag on dark skin
    # (low ITA), where benign longitudinal melanonychia is common.
    assert tone_adjusted_threshold(None) < tone_adjusted_threshold(15.0)
    n = 1100
    across = np.linspace(-NAIL_WIDTH_FRAC, NAIL_WIDTH_FRAC, n)
    V = np.full(n, 0.6)
    V[np.abs(across) < 0.06] = 0.32  # moderate band: contrast ~0.47
    region = _region(S=np.full(n, 0.4), V=V, across=across)
    contrast = band_contrast(region)
    assert contrast_to_verdict(contrast, skin_ita=60.0) == "outside"  # light skin
    assert contrast_to_verdict(contrast, skin_ita=15.0) == "within"   # dark skin


def test_melanonychia_edge_shadow_ignored():
    # A dark stripe at the very edge is finger/nail-edge shadow, not pigment.
    n = 1100
    across = np.linspace(-NAIL_WIDTH_FRAC, NAIL_WIDTH_FRAC, n)
    V = np.full(n, 0.6)
    V[across < -0.5] = 0.2
    region = _region(S=np.full(n, 0.4), V=V, across=across)
    assert contrast_to_verdict(band_contrast(region)) == "within"


# --- nail_region (image path) --------------------------------------------------

def _finger_image(nail_bgr):
    """400x200 black frame with a finger ellipse and a distinct nail ellipse at the
    distal (top) end; nail painted with nail_bgr."""
    import cv2
    img = np.zeros((400, 200, 3), dtype=np.uint8)
    cv2.ellipse(img, (100, 200), (60, 180), 0, 0, 360, (180, 150, 150), -1)  # skin
    cv2.ellipse(img, (100, 90), (35, 70), 0, 0, 360, nail_bgr, -1)           # nail
    return img


def _contour(img):
    from ml.infer.preprocessing import extract_best_contour
    contour, validation = extract_best_contour(img)
    assert validation["is_valid"], validation["reason"]
    return contour


def test_nail_region_found_on_synthetic_finger():
    img = _finger_image((200, 180, 180))  # pinkish, low-saturation nail
    region, reason = compute_nail_region(img, _contour(img))
    assert reason is None
    assert region["region_px"] > 0


def test_nail_region_white_nail_flags_leukonychia():
    img = _finger_image((210, 205, 205))  # near-white, low-saturation nail
    region, reason = compute_nail_region(img, _contour(img))
    assert reason is None
    assert fraction_to_verdict(white_fraction(region)) == "outside"


def test_nail_region_healthy_nail_within_leukonychia():
    img = _finger_image((200, 180, 180))  # value below the white cutoff
    region, reason = compute_nail_region(img, _contour(img))
    assert reason is None
    assert fraction_to_verdict(white_fraction(region)) == "within"
