import numpy as np
import pytest

from ml.infer.clubbing import angle_to_verdict, measure_nail_angle
from ml.infer.koilonychia import measure_nail_curvature, sagitta_to_verdict


def test_right_angle_concave():
    A, B, C = (-1, 0), (0, 0), (0, -1)
    assert measure_nail_angle(A, B, C, cuticle_is_concave=True) == pytest.approx(90.0)


def test_straight_line_is_boundary():
    A, B, C = (-1, 0), (0, 0), (1, 0)
    angle = measure_nail_angle(A, B, C, cuticle_is_concave=True)
    assert angle == pytest.approx(180.0)
    assert angle_to_verdict(angle) == "within"


def test_convex_cuticle_reflects_past_180():
    # Same raw geometry as the right-angle case, but flagged convex (clubbed) --
    # arccos alone caps at 180, so this must come back as the reflex angle.
    A, B, C = (-1, 0), (0, 0), (0, -1)
    angle = measure_nail_angle(A, B, C, cuticle_is_concave=False)
    assert angle == pytest.approx(270.0)
    assert angle_to_verdict(angle) == "outside"


def test_near_straight_convex_just_exceeds_180():
    # A near-flat dorsal line that's slightly convex (not concave) is the
    # realistic clubbing case -- just over 180, not a dramatic bulge.
    A, B, C = (-1, 0), (0, 0), (-np.cos(np.radians(170)), -np.sin(np.radians(170)))
    angle = measure_nail_angle(A, B, C, cuticle_is_concave=False)
    assert angle == pytest.approx(190.0, abs=0.5)
    assert angle_to_verdict(angle) == "outside"


def test_normal_concave_angle_within_range():
    # ~160deg concave notch, the textbook "normal" Lovibond angle. BA points at
    # 180deg; placing C 20deg off the positive x-axis makes the BA-BC angle 160deg.
    theta = np.radians(20)
    A = (-1, 0)
    C = (np.cos(theta), np.sin(theta))
    angle = measure_nail_angle(A, (0, 0), C, cuticle_is_concave=True)
    assert angle == pytest.approx(160.0)
    assert angle_to_verdict(angle) == "within"


def _segment_keypoints(tip_idx, cuticle_idx, direction):
    return {"tip_idx": tip_idx, "cuticle_idx": cuticle_idx, "direction": direction}


def test_koilonychia_convex_segment_is_within():
    # Nail-plate contour bulging away from the chord -- normal convex nail.
    pts = np.array([[0, 0], [2, -0.5], [5, -1], [8, -0.5], [10, 0]], dtype=np.float64)
    keypoints = _segment_keypoints(tip_idx=4, cuticle_idx=0, direction=-1)
    keypoints["B"] = pts[0]
    keypoints["C"] = pts[4]

    sagitta = measure_nail_curvature(pts, keypoints)
    assert sagitta < 0
    assert sagitta_to_verdict(sagitta) == "within"


def test_koilonychia_concave_segment_is_outside():
    # Nail-plate contour scooped toward the chord -- spoon nail.
    pts = np.array([[0, 0], [2, 0.5], [5, 1], [8, 0.5], [10, 0]], dtype=np.float64)
    keypoints = _segment_keypoints(tip_idx=4, cuticle_idx=0, direction=-1)
    keypoints["B"] = pts[0]
    keypoints["C"] = pts[4]

    sagitta = measure_nail_curvature(pts, keypoints)
    assert sagitta > 0
    assert sagitta_to_verdict(sagitta) == "outside"


def test_koilonychia_flat_segment_is_within():
    pts = np.array([[0, 0], [2.5, 0], [5, 0], [7.5, 0], [10, 0]], dtype=np.float64)
    keypoints = _segment_keypoints(tip_idx=4, cuticle_idx=0, direction=-1)
    keypoints["B"] = pts[0]
    keypoints["C"] = pts[4]

    sagitta = measure_nail_curvature(pts, keypoints)
    assert sagitta == pytest.approx(0.0)
    assert sagitta_to_verdict(sagitta) == "within"
