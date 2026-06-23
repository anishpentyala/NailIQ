import base64

import cv2
import numpy as np

MIN_CONTOUR_AREA = 5000

# Focus check: variance of the Laplacian is low for blurry images. Computed on a
# size-normalized copy (below) so the threshold doesn't change with resolution.
# Calibrated against real phone photos: sharp in-focus shots score ~60+, a mild
# Gaussian blur drops to ~10-13, so 20 separates them with margin. Deliberately
# conservative -- a plain-background single-finger shot (what the app asks for)
# has little texture and scores lower even when sharp, so we'd rather pass a
# slightly soft photo than falsely reject a good one. Rough starting estimate.
BLUR_THRESHOLD = 20.0
_BLUR_NORM_DIM = 512


def decode_base64_image(b64_str):
    img_bytes = base64.b64decode(b64_str)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def focus_score(image_bgr):
    """Sharpness metric (variance of Laplacian). Lower = blurrier.

    The image is first scaled to a fixed max dimension so the score -- and thus
    BLUR_THRESHOLD -- means the same thing for a small dataset image and a large
    phone photo.
    """
    h, w = image_bgr.shape[:2]
    scale = _BLUR_NORM_DIM / max(h, w)
    if scale < 1.0:
        image_bgr = cv2.resize(image_bgr, (int(w * scale), int(h * scale)))
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


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


# Padding (fraction of the bbox) left around the finger when cropping the ROI,
# so the cuticle/tip aren't clipped right at the edge.
ROI_PAD_FRAC = 0.15


def crop_to_finger_roi(image_bgr, pad_frac=ROI_PAD_FRAC):
    """Crop to the detected finger's bounding box (with padding).

    The classifier was hurt by background clutter: feeding the whole frame let it
    key off whatever was behind the finger. Cropping to the finger ROI first --
    using the same contour detector the geometry track relies on -- aligns what
    the CNN sees at inference with the tight nail crops it trained on.

    Falls back to the original image when no finger contour is found (e.g. an
    already-cropped dataset image, or a frame the detector can't segment), so it
    never throws and never returns an empty crop.
    """
    contour, validation = extract_best_contour(image_bgr)
    if not validation["is_valid"]:
        return image_bgr

    h, w = image_bgr.shape[:2]
    xs, ys = contour[:, 0], contour[:, 1]
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())

    pad_x = int((x1 - x0) * pad_frac)
    pad_y = int((y1 - y0) * pad_frac)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w, x1 + pad_x)
    y1 = min(h, y1 + pad_y)

    crop = image_bgr[y0:y1, x0:x1]
    return crop if crop.size else image_bgr
