import numpy as np

from ml.infer.image_quality import (
    FOCUS_GOOD,
    GLARE_FRAC_MAX,
    POLISH_FRAC_MAX,
    glare_fraction,
    ita_degrees,
    photo_quality,
    polish_fraction,
    quality_reason,
    white_balance,
)


def test_white_balance_neutralizes_color_cast():
    # A uniform warm-cast image (strong red/low blue in BGR) should come back roughly
    # gray-balanced: the three channel means much closer together than before.
    img = np.full((40, 40, 3), 0, dtype=np.uint8)
    img[..., 0] = 60   # B
    img[..., 1] = 120  # G
    img[..., 2] = 200  # R
    out = white_balance(img)
    means = out.reshape(-1, 3).mean(axis=0)
    assert means.max() - means.min() < 25  # was 140 before balancing


def test_white_balance_preserves_neutral_gray():
    img = np.full((20, 20, 3), 128, dtype=np.uint8)
    out = white_balance(img)
    assert abs(int(out.mean()) - 128) <= 2


def test_ita_lighter_skin_has_higher_angle():
    # Lighter skin: high L*, small b*. Darker: lower L*, larger b*.
    light = ita_degrees(np.full(100, 75.0), np.full(100, 12.0))
    dark = ita_degrees(np.full(100, 35.0), np.full(100, 22.0))
    assert light > dark


def test_ita_handles_degenerate_input():
    assert ita_degrees(np.array([]), np.array([])) is None
    assert ita_degrees(np.full(5, 60.0), np.zeros(5)) is None


def test_glare_and_polish_fractions():
    V = np.concatenate([np.full(30, 0.99), np.full(70, 0.6)])
    assert glare_fraction(V) == 0.3
    S = np.concatenate([np.full(60, 0.8), np.full(40, 0.1)])
    assert polish_fraction(S) == 0.6


def test_quality_reason_flags_polish_then_glare():
    # Mostly-saturated region -> polish.
    assert quality_reason(np.full(100, 0.6), np.full(100, 0.8)) == "nail_polish_detected"
    # Low saturation but heavy glare -> glare.
    glary = np.concatenate([np.full(40, 0.99), np.full(60, 0.6)])
    assert quality_reason(glary, np.full(100, 0.1)) == "too_much_glare"
    # Clean low-sat, low-glare region -> fine.
    assert quality_reason(np.full(100, 0.6), np.full(100, 0.1)) is None


def test_quality_thresholds_are_boundaries():
    assert POLISH_FRAC_MAX == 0.5
    assert GLARE_FRAC_MAX == 0.25


def test_photo_quality_sharp_clean_is_good():
    q = photo_quality(FOCUS_GOOD, glare_frac=0.0, polish_frac=0.0)
    assert q["score"] == 100
    assert q["band"] == "good"
    assert q["issues"] == []


def test_photo_quality_blurry_is_poor():
    q = photo_quality(focus=10.0, glare_frac=0.0, polish_frac=0.0)
    assert q["band"] == "poor"
    assert "blurry" in q["issues"]


def test_photo_quality_weakest_link_caps_score():
    # Crisp focus, but heavy glare past its budget -> glare caps the score.
    q = photo_quality(FOCUS_GOOD, glare_frac=GLARE_FRAC_MAX, polish_frac=0.0)
    assert q["score"] == 0
    assert "glare" in q["issues"]
    # Polish over budget flags polish.
    q = photo_quality(FOCUS_GOOD, glare_frac=0.0, polish_frac=POLISH_FRAC_MAX)
    assert "polish" in q["issues"]


def test_photo_quality_side_photo_focus_only():
    # No colour sampling on the side view: glare/polish default to no penalty.
    q = photo_quality(FOCUS_GOOD)
    assert q["score"] == 100
    assert q["issues"] == []
