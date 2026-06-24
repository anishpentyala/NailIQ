from . import (
    beaus_lines,
    classifier,
    clubbing,
    fusion,
    koilonychia,
    leukonychia,
    melanonychia,
    nail_region,
    pitting,
    splinter_hemorrhages,
    terrys_nails,
)
from .keypoints import find_keypoints
from .preprocessing import BLUR_THRESHOLD, decode_base64_image, extract_best_contour, focus_score

# Color/texture conditions measured from the top-down nail region, in display order.
_COLOR_CONDITIONS = (
    leukonychia,
    melanonychia,
    terrys_nails,
    beaus_lines,
    splinter_hemorrhages,
    pitting,
)


def _inconclusive_findings(failure_reason):
    return [
        clubbing.inconclusive_finding(failure_reason),
        koilonychia.inconclusive_finding(failure_reason),
    ]


def _color_inconclusive(failure_reason):
    return [c.inconclusive_finding(failure_reason) for c in _COLOR_CONDITIONS]


def _extract(image_b64, require_keypoints=True):
    """Decode + locate a finger contour, optionally also its A/B/C keypoints.

    Returns (contour, keypoints, failure_reason). keypoints is None and
    failure_reason is set on any rejection; keypoints stays None (with no
    failure) when require_keypoints=False and only a contour is needed, e.g.
    validating the top-down photo, which isn't shaped like a side profile so
    the cuticle-vertex search doesn't apply to it.
    """
    image = decode_base64_image(image_b64)
    if image is None:
        return None, None, "invalid_image"

    if focus_score(image) < BLUR_THRESHOLD:
        return None, None, "too_blurry"

    contour, contour_validation = extract_best_contour(image)
    if not contour_validation["is_valid"]:
        return None, None, contour_validation["reason"]

    if not require_keypoints:
        return contour, None, None

    keypoints, kp_validation = find_keypoints(contour)
    if not kp_validation["is_valid"]:
        return contour, None, kp_validation["reason"]

    return contour, keypoints, None


def validate_photo(image_b64, require_keypoints=True):
    """Quick check used right after capture, before the full /analyze round trip."""
    _, _, failure_reason = _extract(image_b64, require_keypoints=require_keypoints)
    return failure_reason is None, failure_reason


def analyze_side_profile(side_image_b64):
    """Geometry-only findings (clubbing angle + koilonychia sagitta) from the side photo."""
    contour, keypoints, failure_reason = _extract(side_image_b64, require_keypoints=True)
    if failure_reason:
        return {"findings": _inconclusive_findings(failure_reason)}

    confidence = keypoints["confidence"]
    findings = [
        clubbing.build_finding(
            keypoints["A"], keypoints["B"], keypoints["C"], keypoints["cuticle_is_concave"], confidence
        ),
        koilonychia.build_finding(contour, keypoints, confidence),
    ]
    return {"findings": findings}


def _ml_finding(image_b64, view):
    """One trained-CNN finding for a photo, or None if it can't be produced."""
    image = decode_base64_image(image_b64)
    if image is None:
        return None
    try:
        return classifier.build_finding(image, view)
    except Exception:  # noqa: BLE001 -- ML track must never break the geometry response
        return None


def analyze_top_color(top_image_b64):
    """Color/texture findings (see _COLOR_CONDITIONS) from the top-down photo.

    Classical CV like the geometry track -- no trained model needed, so this runs
    even in a torch-free environment. The top-down view is the right one for these:
    they're about the nail plate's color, not its side-profile shape. On any photo
    failure both color findings come back inconclusive with the same reason rather
    than measuring color on a region that wasn't reliably located.
    """
    image = decode_base64_image(top_image_b64)
    if image is None:
        return _color_inconclusive("invalid_image")
    if focus_score(image) < BLUR_THRESHOLD:
        return _color_inconclusive("too_blurry")
    contour, validation = extract_best_contour(image)
    if not validation["is_valid"]:
        return _color_inconclusive(validation["reason"])
    region, reason = nail_region.compute_nail_region(image, contour)
    if reason:
        return _color_inconclusive(reason)
    return [c.build_finding(region) for c in _COLOR_CONDITIONS]


def analyze(side_image_b64, top_image_b64):
    """Full response: geometry (side photo) fused with the trained-CNN track, plus
    the color/texture track on the top-down photo.

    Geometry measures the side profile. The CNN classifies the top-down photo
    (its trained view), and fusion.fuse() combines the two into one finding per
    geometry condition: agreeing tracks boost confidence, disagreeing tracks return
    inconclusive rather than asserting a split verdict. The color track adds its own
    standalone findings (leukonychia, melanonychia, Terry's nails, Beau's lines,
    splinter hemorrhages, pitting) from the top-down photo.

    If torch or the weights aren't present (classifier.is_available() is False), the
    geometry findings stand on their own unchanged; the color track runs regardless
    -- the app still works, with full color findings, in a torch-free environment.
    """
    geometry = analyze_side_profile(side_image_b64)["findings"]
    color = analyze_top_color(top_image_b64)
    if not classifier.is_available():
        return {"findings": geometry + color}

    ml_top = _ml_finding(top_image_b64, "top")
    return {"findings": fusion.fuse(geometry, ml_top) + color}
