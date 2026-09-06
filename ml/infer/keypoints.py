import numpy as np

# Tip must be reasonably pointed, not flat/blurry. Larger fitted-circle radius
# means a blunter tip; this is a rough heuristic, not a calibrated threshold.
MIN_TIP_PROMINENCE = 0.02

# Cuticle vertex is the sharpest curvature discontinuity found in this arc-length
# window (as a fraction of total contour length) on either side of the fingertip,
# excluding the tip's own curvature peak.
CUTICLE_SEARCH_START_FRAC = 0.08
CUTICLE_SEARCH_END_FRAC = 0.35
CUTICLE_MIN_CURVATURE_SCORE = 0.05

# Point A (proximal skin) is sampled further along the same direction past B.
NAIL_FOLD_OFFSET_FRAC = 0.12

MIN_KEYPOINT_DISTANCE = 5
COLLINEARITY_CROSS_THRESHOLD = 10

# How close (in pixels) the detected tip may sit to the frame edge it isn't
# entering from before we call it cropped rather than just close to frame. Rough
# starting estimate, not calibrated against a labeled dataset.
TIP_BORDER_MARGIN_PX = 8

# Which contour extremum is "farthest from the entry edge" (i.e. the fingertip),
# keyed by the edge the hand enters the frame from. `argmax(y)` (entry from the
# top) is also the behavior with no known entry edge at all -- padded dataset
# crops never touch a border, so they always take that branch unchanged.
_TIP_SELECTORS = {
    "top": lambda pts: int(np.argmax(pts[:, 1])),
    "bottom": lambda pts: int(np.argmin(pts[:, 1])),
    "left": lambda pts: int(np.argmax(pts[:, 0])),
    "right": lambda pts: int(np.argmin(pts[:, 0])),
    None: lambda pts: int(np.argmax(pts[:, 1])),
}


def _fit_circle(points):
    x = points[:, 0].astype(np.float64)
    y = points[:, 1].astype(np.float64)
    A = np.column_stack([x, y, np.ones(len(x))])
    b = x**2 + y**2
    params, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = params[0] / 2, params[1] / 2
    radius_sq = params[2] + cx**2 + cy**2
    radius = np.sqrt(radius_sq) if radius_sq > 0 else float("inf")
    return (cx, cy), radius


def find_fingertip(pts, window=5, entry_edge=None):
    """Locate the fingertip as the contour extremum farthest from wherever the
    hand enters the frame.

    `entry_edge` names the border the contour touches ("top"/"bottom"/"left"/
    "right", from preprocessing.extract_finger_contour's border_edges) -- the
    fingertip is the opposite extremum. With `entry_edge=None` (no border
    contact -- the case for every padded dataset crop today), this falls back
    to the original `argmax(y)` rule byte-for-byte, so dataset accuracy can't
    move. Real photos, where the hand always continues off-frame on one side,
    are the only callers that ever pass a non-None entry_edge.
    """
    tip_idx = _TIP_SELECTORS.get(entry_edge, _TIP_SELECTORS[None])(pts)

    n = len(pts)
    idxs = [(tip_idx + i) % n for i in range(-window, window + 1)]
    local = pts[idxs].astype(np.float64)

    if len(local) >= 3:
        _, radius = _fit_circle(local)
        prominence = 1.0 / radius if radius > 0 else 0.0
    else:
        prominence = 0.0

    return tip_idx, prominence


def _tip_is_cropped(pts, tip_idx, frame_size, margin_px=TIP_BORDER_MARGIN_PX):
    """True if the located tip itself sits within margin_px of any frame edge --
    i.e. even after picking the extremum farthest from the entry side, the tip
    is still hugging some border, so it's likely genuinely cut off rather than
    just entering the frame normally."""
    if frame_size is None:
        return False
    w, h = frame_size
    x, y = pts[tip_idx]
    return min(x, w - 1 - x, y, h - 1 - y) < margin_px


def _discrete_curvature(pts, idx, step=3):
    n = len(pts)
    prev_pt = pts[(idx - step) % n].astype(np.float64)
    cur_pt = pts[idx].astype(np.float64)
    next_pt = pts[(idx + step) % n].astype(np.float64)

    v1 = cur_pt - prev_pt
    v2 = next_pt - cur_pt
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    norm = (np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-6
    return cross / norm


def find_cuticle_vertex(pts, tip_idx):
    n = len(pts)
    start = int(n * CUTICLE_SEARCH_START_FRAC)
    end = int(n * CUTICLE_SEARCH_END_FRAC)

    best_score = 0.0
    best_idx = None
    best_dir = 1

    for direction in (1, -1):
        for i in range(start, end):
            idx = (tip_idx + direction * i) % n
            curvature = _discrete_curvature(pts, idx)
            if abs(curvature) > abs(best_score):
                best_score = curvature
                best_idx = idx
                best_dir = direction

    # Signed: callers compare this sign against the (always-convex) fingertip's
    # curvature sign to tell a concave cuticle notch from a convex/clubbed one.
    return best_idx, best_dir, best_score


def find_keypoints(pts, entry_edge=None, frame_size=None):
    """entry_edge/frame_size come from preprocessing's contour validation dict
    (border_edges/frame_size) -- see find_fingertip for what entry_edge selects
    and why entry_edge=None reproduces the original dataset-only behavior."""
    n = len(pts)
    tip_idx, prominence = find_fingertip(pts, entry_edge=entry_edge)

    if prominence < MIN_TIP_PROMINENCE:
        return None, {"is_valid": False, "reason": "fingertip_not_clear"}

    if _tip_is_cropped(pts, tip_idx, frame_size):
        return None, {"is_valid": False, "reason": "fingertip_cropped"}

    cuticle_idx, direction, cuticle_curvature_signed = find_cuticle_vertex(pts, tip_idx)
    curvature_score = abs(cuticle_curvature_signed)

    if cuticle_idx is None or curvature_score < CUTICLE_MIN_CURVATURE_SCORE:
        return None, {"is_valid": False, "reason": "cuticle_not_detected"}

    fold_offset = int(n * NAIL_FOLD_OFFSET_FRAC)
    fold_idx = (cuticle_idx + direction * fold_offset) % n

    A = pts[fold_idx]
    B = pts[cuticle_idx]
    C = pts[tip_idx]

    valid, reason = _validate_triangle(A, B, C)
    if not valid:
        return None, {"is_valid": False, "reason": reason}

    # The fingertip is always a convex bump regardless of clubbing status, so its
    # curvature sign is a reliable reference for "convex" on this contour's
    # winding direction. A cuticle vertex with the opposite sign is a concave
    # notch (normal profile); the same sign means it's convex too (clubbed profile,
    # the dorsal line bulges rather than dips at the cuticle).
    tip_curvature_signed = _discrete_curvature(pts, tip_idx)
    cuticle_is_concave = bool(np.sign(cuticle_curvature_signed) != np.sign(tip_curvature_signed))

    quality = min(1.0, 0.5 * prominence / MIN_TIP_PROMINENCE) + min(
        0.5, 0.5 * curvature_score / (CUTICLE_MIN_CURVATURE_SCORE * 4)
    )

    return {
        "A": A,
        "B": B,
        "C": C,
        "tip_idx": tip_idx,
        "cuticle_idx": cuticle_idx,
        "direction": direction,
        "cuticle_is_concave": cuticle_is_concave,
        "confidence": float(np.clip(quality, 0.0, 1.0)),
    }, {"is_valid": True, "reason": None}


def _validate_triangle(A, B, C):
    A, B, C = np.asarray(A, dtype=np.float64), np.asarray(B, dtype=np.float64), np.asarray(C, dtype=np.float64)

    dist_AB = np.linalg.norm(A - B)
    dist_BC = np.linalg.norm(B - C)

    if dist_AB < MIN_KEYPOINT_DISTANCE or dist_BC < MIN_KEYPOINT_DISTANCE:
        return False, "points_too_close"

    cross = (A[0] - B[0]) * (C[1] - B[1]) - (A[1] - B[1]) * (C[0] - B[0])
    if abs(cross) < COLLINEARITY_CROSS_THRESHOLD:
        return False, "points_collinear"

    return True, None
