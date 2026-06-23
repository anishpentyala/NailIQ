from . import classifier, clubbing, koilonychia
from .keypoints import find_keypoints
from .preprocessing import decode_base64_image, extract_best_contour


def _inconclusive_findings(failure_reason):
    return [
        clubbing.inconclusive_finding(failure_reason),
        koilonychia.inconclusive_finding(failure_reason),
    ]


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


def analyze(side_image_b64, top_image_b64):
    """Full response: geometry track (side photo) + trained-CNN track (both photos).

    The classifier runs on both views as two separate findings; if torch or the
    weights aren't present (classifier.is_available() is False) the ML findings
    are simply omitted and the geometry findings stand on their own.
    """
    result = analyze_side_profile(side_image_b64)
    if classifier.is_available():
        for view, b64 in (("side", side_image_b64), ("top", top_image_b64)):
            finding = _ml_finding(b64, view)
            if finding is not None:
                result["findings"].append(finding)
    return result
