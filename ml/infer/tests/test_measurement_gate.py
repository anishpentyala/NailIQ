"""measurement_gate: geometry verdicts only when the measurement is reproducible."""
import cv2
import numpy as np
import pytest

from ml.infer import measurement_gate
from ml.infer.keypoints import find_keypoints
from ml.infer.preprocessing import extract_best_contour
from ml.infer.tests.test_framing import _finger_polygon


def _raster_finger(scale, notch_depth):
    pts = _finger_polygon(notch_depth=notch_depth) * scale
    img = np.full((int(pts[:, 1].max()) + 1, int(pts[:, 0].max()) + 60, 3), 235, np.uint8)
    cv2.fillPoly(img, [pts.astype(np.int32)], (120, 150, 200))
    return cv2.GaussianBlur(img, (3, 3), 0)


def _keypoints(img):
    contour, validation = extract_best_contour(img)
    assert validation["is_valid"]
    kp, kv = find_keypoints(contour, entry_edge=validation.get("primary_edge"),
                            frame_size=validation.get("frame_size"))
    assert kv["is_valid"], kv
    return contour, kp


@pytest.mark.parametrize("scale", [2, 3, 4, 5])
@pytest.mark.parametrize("depth", [16, 22])
def test_clean_finger_is_stable_at_every_size(scale, depth):
    """Before the scale-relative curvature step, several of these flipped verdict under
    a 0.8x/1.25x rescale -- the same anatomy must measure the same at any photo size.
    (A shallower notch, depth 10, measures ~175deg: inside the guard band by design.)"""
    img = _raster_finger(scale, depth)
    contour, kp = _keypoints(img)
    reason, stability = measurement_gate.check(img, contour, kp)
    assert reason is None
    assert 0.5 <= stability <= 1.0


def test_implausible_angle_abstains(monkeypatch):
    img = _raster_finger(3, 16)
    contour, kp = _keypoints(img)
    monkeypatch.setattr(measurement_gate.clubbing, "measure_nail_angle", lambda *a: 290.0)
    assert measurement_gate.check(img, contour, kp) == ("angle_implausible", 0.0)


def test_near_threshold_angle_abstains(monkeypatch):
    img = _raster_finger(3, 16)
    contour, kp = _keypoints(img)
    monkeypatch.setattr(measurement_gate.clubbing, "measure_nail_angle", lambda *a: 182.6)
    assert measurement_gate.check(img, contour, kp) == ("measurement_borderline", 0.0)


def test_verdict_flip_under_perturbation_abstains(monkeypatch):
    """Simulates the real-photo failure: the as-captured photo measures 'within' but a
    re-saved copy measures 'outside'."""
    img = _raster_finger(3, 16)
    contour, kp = _keypoints(img)
    calls = iter([160.0, 160.0, 214.3, 160.0, 160.0, 160.0])
    monkeypatch.setattr(measurement_gate.clubbing, "measure_nail_angle", lambda *a: next(calls))
    assert measurement_gate.check(img, contour, kp) == ("measurement_unstable", 0.0)
