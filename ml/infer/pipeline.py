from . import clubbing, koilonychia
from .keypoints import find_keypoints
from .preprocessing import decode_base64_image, extract_finger_contour, preprocess_and_threshold


def _inconclusive_findings(failure_reason):
    return [
        clubbing.inconclusive_finding(failure_reason),
        koilonychia.inconclusive_finding(failure_reason),
    ]


def analyze_side_profile(side_image_b64):
    image = decode_base64_image(side_image_b64)
    if image is None:
        return {"findings": _inconclusive_findings("invalid_image")}

    binary_mask = preprocess_and_threshold(image)
    contour, contour_validation = extract_finger_contour(binary_mask)

    if not contour_validation["is_valid"]:
        return {"findings": _inconclusive_findings(contour_validation["reason"])}

    keypoints, kp_validation = find_keypoints(contour)

    if not kp_validation["is_valid"]:
        return {"findings": _inconclusive_findings(kp_validation["reason"])}

    confidence = keypoints["confidence"]
    findings = [
        clubbing.build_finding(
            keypoints["A"], keypoints["B"], keypoints["C"], keypoints["cuticle_is_concave"], confidence
        ),
        koilonychia.build_finding(contour, keypoints, confidence),
    ]
    return {"findings": findings}
