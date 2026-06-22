import base64

import cv2
import numpy as np

MIN_CONTOUR_AREA = 5000


def decode_base64_image(b64_str):
    img_bytes = base64.b64decode(b64_str)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def preprocess_and_threshold(image_bgr, bg_color="light"):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)

    if bg_color == "light":
        # Finger is darker than a light background.
        _, binary = cv2.threshold(blurred, 150, 255, cv2.THRESH_BINARY_INV)
    else:
        # Finger is lighter than a dark background.
        _, binary = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    return cleaned


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
