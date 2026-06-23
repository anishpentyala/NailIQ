from . import clubbing, koilonychia
from .keypoints import find_keypoints
from .preprocessing import decode_base64_image, extract_finger_contour, preprocess_and_threshold


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

    binary_mask = preprocess_and_threshold(image)
    contour, contour_validation = extract_finger_contour(binary_mask)
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
