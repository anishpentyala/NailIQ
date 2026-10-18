"""Optional detector and shared validation for normalized user-selected nail boxes."""
import json
import math
from pathlib import Path

import cv2

from . import image_quality
from .preprocessing import BLUR_THRESHOLD, focus_score, is_flat_frame

_MODELS = Path(__file__).resolve().parents[1] / 'models'
_state = {}


def valid_bbox(box):
    return (isinstance(box, (list, tuple)) and len(box) == 4
            and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) for value in box)
            and 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)


def pixel_box(image, box):
    h, w = image.shape[:2]
    return [int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)]


def roi_quality(image, box):
    if not valid_bbox(box):
        return 'invalid_nail_bbox'
    x0, y0, x1, y1 = pixel_box(image, box)
    if x1 - x0 < 24 or y1 - y0 < 24:
        return 'nail_region_unclear'
    crop = image[y0:y1, x0:x1]
    if is_flat_frame(crop):
        return 'nail_region_unclear'
    # The classifier includes the cuticle/plate boundary in its 15% padded crop.
    # Measuring only the smooth interior mistakes low texture for camera blur.
    from .color_classifier import _crop_to_bbox
    if focus_score(_crop_to_bbox(image, box)) < BLUR_THRESHOLD:
        return 'too_blurry'
    hsv = cv2.cvtColor(image_quality.white_balance(crop), cv2.COLOR_BGR2HSV)
    return image_quality.quality_reason(hsv[..., 2].ravel() / 255, hsv[..., 1].ravel() / 255)


def detect(image):
    metadata_path = _MODELS / 'nail_locator.json'
    if not metadata_path.is_file():
        return []
    try:
        metadata = json.loads(metadata_path.read_text())
        if not isinstance(metadata, dict):
            return []
        weights = _MODELS / metadata.get('weights_file', 'nail_locator.pt')
        if not weights.is_file():
            return []
        import torch
        from ml.nail_detection_model import build_nail_detector
        identity = (str(weights), weights.stat().st_mtime_ns)
        if _state.get('identity') != identity:
            model = build_nail_detector()
            model.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True))
            _state.update(identity=identity, model=model.eval())
        tensor = torch.from_numpy(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 255
        with torch.inference_mode():
            result = _state['model']([tensor])[0]
        h, w = image.shape[:2]
        boxes = []
        for box, score in zip(result['boxes'].tolist(), result['scores'].tolist()):
            normalized = [max(0, min(1, value / size)) for value, size in zip(box, (w, h, w, h))]
            if score >= metadata.get('threshold', 0.5) and valid_bbox(normalized):
                boxes.append({'bbox': normalized, 'confidence': score})
        return sorted(boxes, key=lambda row: row['confidence'], reverse=True)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        return []
