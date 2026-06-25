from . import (
    beaus_lines,
    classifier,
    clubbing,
    color_classifier,
    color_fusion,
    cyanosis,
    fusion,
    koilonychia,
    leukonychia,
    lindsays_nails,
    melanonychia,
    muehrckes_lines,
    nail_region,
    onycholysis,
    pallor,
    pitting,
    splinter_hemorrhages,
    terrys_nails,
)
from .keypoints import find_keypoints
from .preprocessing import BLUR_THRESHOLD, decode_base64_image, extract_best_contour, focus_score

# Color/texture conditions measured from the top-down nail region, in display order
# (grouped: overall colour, then proximal/distal patterns, then surface markings).
_COLOR_CONDITIONS = (
    leukonychia,
    melanonychia,
    pallor,
    cyanosis,
    terrys_nails,
    lindsays_nails,
    onycholysis,
    beaus_lines,
    muehrckes_lines,
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

    Returns (findings, overlay). overlay is {"top_bbox_norm": [x0,y0,x1,y1] in 0..1,
    "skin_ita": float|None} when the nail region was located (so the UI can show
    *what* was measured), else {"top_bbox_norm": None, "skin_ita": None}.

    Classical CV like the geometry track -- no trained model needed, so this runs
    even in a torch-free environment. The top-down view is the right one for these:
    they're about the nail plate's color, not its side-profile shape. On any photo
    failure the color findings come back inconclusive with the same reason rather
    than measuring color on a region that wasn't reliably located.
    """
    no_overlay = {"top_bbox_norm": None, "skin_ita": None}
    image = decode_base64_image(top_image_b64)
    if image is None:
        return _color_inconclusive("invalid_image"), no_overlay
    if focus_score(image) < BLUR_THRESHOLD:
        return _color_inconclusive("too_blurry"), no_overlay
    contour, validation = extract_best_contour(image)
    if not validation["is_valid"]:
        return _color_inconclusive(validation["reason"]), no_overlay
    region, reason = nail_region.compute_nail_region(image, contour)
    if reason:
        return _color_inconclusive(reason), no_overlay
    findings = [c.build_finding(region) for c in _COLOR_CONDITIONS]

    # Optional trained-CNN second opinion: where it has a confident call on one of its
    # covered conditions it leads, else the classical heuristic stands (see color_fusion).
    # Gated by is_available() and wrapped so the CNN can never break the classical track.
    if color_classifier.is_available():
        try:
            pred = color_classifier.predict_from_region(image, region)
            findings = color_fusion.fuse(findings, pred, color_classifier.app_conditions())
        except Exception:  # noqa: BLE001 -- ML must never break the color response
            pass

    overlay = {"top_bbox_norm": list(region["bbox_norm"]), "skin_ita": region["skin_ita"]}
    return findings, overlay


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
    color, overlay = analyze_top_color(top_image_b64)
    if not classifier.is_available():
        return {"findings": geometry + color, "overlay": overlay}

    ml_top = _ml_finding(top_image_b64, "top")
    return {"findings": fusion.fuse(geometry, ml_top) + color, "overlay": overlay}
