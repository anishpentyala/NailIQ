"""Coverage for the real-photo framing bugs fixed in preprocessing.py/keypoints.py
(see CLAUDE.md): border rejection and fingertip orientation had zero test coverage
before this, which is exactly how a photo of a real hand -- which always touches a
frame edge, and can point any direction -- went unnoticed as broken. Every other
test in this package uses synthetic shapes that never touch a border and always
point "down" like the training dataset; these deliberately do the opposite.
"""
import cv2
import numpy as np

from ml.infer.keypoints import _tip_is_cropped, find_fingertip, find_keypoints
from ml.infer.preprocessing import extract_finger_contour


def _finger_polygon(half_w=20, tip_r=20, notch_center_y=140, notch_depth=12,
                     notch_width=40, base_y=300, step=2, y_offset=30):
    """A hand-built finger silhouette (not rasterized -- cv2 boolean ops between
    primitives create sharp corner artifacts at the seams whose spurious
    curvature swamps the real signal, which is exactly what made an earlier
    draft of this test unreliable): a rounded tip cap, and a single smooth
    concave dent (cosine taper, continuous with its neighbors -- no corners) on
    the left side standing in for a normal nail fold. Built pointing "up" (tip
    at small y, base at large y); test cases transform this into the other
    three orientations directly in point-coordinate space.
    """
    cap = [
        (half_w * np.cos(rad), tip_r - half_w * np.sin(rad))
        for rad in np.radians(np.linspace(0, 180, 40))
    ]
    left = []
    y = tip_r + step
    while y <= base_y:
        dx = 0.0
        d = y - notch_center_y
        if abs(d) < notch_width / 2:
            dx = notch_depth * np.cos(np.pi * d / notch_width) ** 2
        left.append((-half_w + dx, float(y)))
        y += step
    right = [(half_w, float(y)) for y in np.arange(base_y, tip_r, -step)]
    pts = np.array(cap + left + right, dtype=np.float64)
    pts[:, 0] -= pts[:, 0].min() - 10
    pts[:, 1] += y_offset
    return pts


def _normalize(pts):
    pts = pts.copy()
    pts[:, 0] -= pts[:, 0].min() - 10
    pts[:, 1] -= pts[:, 1].min() - 10
    return pts.astype(np.int32)


# Each transform rotates the canonical (tip-up) polygon so the base ends up on
# the named edge instead -- verified against find_fingertip's own edge->tip
# mapping below, not just assumed.
_ORIENTED_POLYGONS = {
    "bottom": lambda base: _normalize(base.copy()),
    "top": lambda base: _normalize(np.column_stack([base[:, 0], -base[:, 1]])),
    "right": lambda base: _normalize(np.column_stack([base[:, 1], base[:, 0]])),
    "left": lambda base: _normalize(np.column_stack([-base[:, 1], base[:, 0]])),
}

_OPPOSITE_EXTREMUM = {
    "top": lambda pts: int(np.argmax(pts[:, 1])),
    "bottom": lambda pts: int(np.argmin(pts[:, 1])),
    "left": lambda pts: int(np.argmax(pts[:, 0])),
    "right": lambda pts: int(np.argmin(pts[:, 0])),
}


def test_fingertip_lands_on_correct_extremum_in_every_orientation():
    """The direct regression test for the 295-degree false-positive bug: with
    entry_edge supplied, the tip must be the extremum FARTHEST from the edge the
    hand enters from, not always the bottommost point."""
    base = _finger_polygon()
    for entry_edge, transform in _ORIENTED_POLYGONS.items():
        pts = transform(base)
        tip_idx, prominence = find_fingertip(pts, entry_edge=entry_edge)
        expected_idx = _OPPOSITE_EXTREMUM[entry_edge](pts)
        assert tip_idx == expected_idx, f"entry={entry_edge}"
        assert prominence > 0, f"entry={entry_edge}: tip not prominent"


def test_find_keypoints_succeeds_and_reports_concave_in_every_orientation():
    """Full find_keypoints() on a shape with a genuine (concave, i.e. normal
    profile) notch must succeed and report cuticle_is_concave=True regardless of
    which way the finger is rotated -- if orientation leaked into the concavity
    sign comparison, this is where a clubbing false-positive would reappear."""
    base = _finger_polygon()
    for entry_edge, transform in _ORIENTED_POLYGONS.items():
        pts = transform(base)
        frame_size = (int(pts[:, 0].max()) + 20, int(pts[:, 1].max()) + 20)
        kp, kp_validation = find_keypoints(pts, entry_edge=entry_edge, frame_size=frame_size)
        assert kp_validation["is_valid"], f"entry={entry_edge}: {kp_validation['reason']}"
        assert kp["cuticle_is_concave"] is True, f"entry={entry_edge}: expected concave (normal) profile"


def _rect_mask(x0, y0, x1, y1, w, h):
    """A simple bar, optionally touching an edge (x1==w-1 or y1==h-1, or
    x0==0 or y0==0) -- just enough shape for extract_finger_contour's
    border-counting logic, no keypoint geometry needed here."""
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(mask, (x0, y0), (x1, y1), 255, -1)
    return mask


def test_single_edge_entry_validates_in_every_orientation():
    """A finger entering from exactly one edge is normal framing, not a cropped
    photo -- it must validate regardless of which edge that is. Uses real
    rasterized masks (unlike the two tests above) to exercise
    extract_finger_contour's actual border-touch counting, not just the
    downstream keypoint math."""
    masks = {
        "bottom": lambda: _rect_mask(80, 140, 120, 299, w=200, h=300),
        "top": lambda: _rect_mask(80, 0, 120, 159, w=200, h=300),
        "left": lambda: _rect_mask(0, 80, 159, 120, w=300, h=200),
        "right": lambda: _rect_mask(140, 80, 299, 120, w=300, h=200),
    }
    for name, build in masks.items():
        contour, validation = extract_finger_contour(build())
        assert validation["is_valid"], f"{name}: {validation['reason']}"
        assert validation["border_edges"] == [name], f"{name}: {validation['border_edges']}"


def test_no_border_contact_falls_back_to_legacy_argmax_y():
    """The backward-compatibility hinge: every padded dataset crop today has no
    border contact, so entry_edge=None must reproduce the exact original
    argmax(y) behavior byte-for-byte, or dataset accuracy would move."""
    # Well clear of every edge on all sides (simulates a padded dataset crop).
    mask = _rect_mask(150, 140, 190, 340, w=400, h=500)

    contour, validation = extract_finger_contour(mask)
    assert validation["is_valid"]
    assert validation["border_edges"] == []

    tip_idx, _ = find_fingertip(contour, entry_edge=None)
    assert tip_idx == int(np.argmax(contour[:, 1]))


def test_three_edges_touched_is_background_not_filling_frame():
    """The real photos' actual signature: the plain background doesn't fill the
    frame, so dark surface beyond it merges into the foreground blob and spans
    three or more edges. Genuinely unanalyzable -- must reject, with the honest
    reason (not the old, misleading 'recenter your finger')."""
    mask = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(mask, (0, 100), (199, 199), 255, -1)  # touches left, right, bottom
    contour, validation = extract_finger_contour(mask)
    assert not validation["is_valid"]
    assert validation["reason"] == "background_not_filling_frame"


def test_two_edge_corner_entry_still_validates():
    """A finger entering at a corner (two edges) is still normal framing."""
    mask = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(mask, (0, 0), (100, 100), 255, -1)  # touches left and top
    contour, validation = extract_finger_contour(mask)
    assert validation["is_valid"]
    assert set(validation["border_edges"]) == {"left", "top"}


def test_tip_cropped_when_tip_hugs_a_border():
    """Even after picking the extremum farthest from the entry edge, a tip that's
    still within the margin of some border is likely genuinely cut off, not just
    normally framed -- this is the case the border rule alone can't catch, since
    it only looks at contour touches, not where the selected tip landed."""
    pts = np.array([[50, 3], [40, 50], [60, 50], [50, 100]], dtype=np.int32)
    tip_idx = 0  # pts[0] = (50, 3), 3px from the top edge
    assert _tip_is_cropped(pts, tip_idx, frame_size=(100, 150), margin_px=8)


def test_tip_not_cropped_when_clear_of_borders():
    pts = np.array([[50, 30], [40, 50], [60, 50], [50, 100]], dtype=np.int32)
    assert not _tip_is_cropped(pts, 0, frame_size=(100, 150), margin_px=8)


def test_tip_cropped_check_is_noop_without_frame_size():
    pts = np.array([[50, 0], [40, 50], [60, 50], [50, 100]], dtype=np.int32)
    assert not _tip_is_cropped(pts, 0, frame_size=None)
