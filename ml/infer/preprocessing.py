import base64

import cv2
import numpy as np

MIN_CONTOUR_AREA = 5000


def decode_base64_image(b64_str):
    img_bytes = base64.b64decode(b64_str)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def preprocess_and_threshold(image_bgr, polarity="auto"):
    """Threshold the frame into a finger/background binary mask.

    A fixed gray-value cutoff (e.g. "below 150 is finger") only works for one
    specific lighting/background combo and fails on most real webcam shots, so
    this uses Otsu's method to pick the cutoff automatically from the image's
    own histogram. Since Otsu only finds *a* boundary, not which side is the
    finger, polarity="auto" returns both readings (THRESH_BINARY and its
    inverse) and the caller picks whichever yields a valid contour.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def _clean(mask):
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        return mask

    _, dark_fg = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, light_fg = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if polarity == "dark_finger":
        return _clean(dark_fg)
    if polarity == "light_finger":
        return _clean(light_fg)
    return [_clean(dark_fg), _clean(light_fg)]


def extract_finger_contour(binary_mask, min_area=MIN_CONTOUR_AREA):
    contours, _ = cv2.findContours(
        binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    if not contours:
        return None, {"is_valid": False, "reason": "no_contour_found"}

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    if area < min_area:
        return None, {"is_valid": False, "reason": "contour_too_small"}

    h, w = binary_mask.shape
    pts = largest.squeeze(axis=1)
    if pts.ndim != 2:
        return None, {"is_valid": False, "reason": "contour_degenerate"}

    touches_border = (
        np.any(pts[:, 0] <= 0)
        or np.any(pts[:, 0] >= w - 1)
        or np.any(pts[:, 1] <= 0)
        or np.any(pts[:, 1] >= h - 1)
    )
    if touches_border:
        return None, {"is_valid": False, "reason": "contour_touches_border"}

    return pts, {"is_valid": True, "reason": None, "area": area}


def extract_best_contour(image_bgr, min_area=MIN_CONTOUR_AREA):
    """Try both threshold polarities, return the first contour that validates.

    If neither polarity produces a valid contour, returns the failure from
    whichever attempt got furthest (a contour that was found but rejected is
    a more useful reason to surface than "no contour found").
    """
    best_failure = {"is_valid": False, "reason": "no_contour_found"}
    for mask in preprocess_and_threshold(image_bgr, polarity="auto"):
        contour, validation = extract_finger_contour(mask, min_area=min_area)
        if validation["is_valid"]:
            return contour, validation
        if best_failure["reason"] == "no_contour_found":
            best_failure = validation
    return None, best_failure
