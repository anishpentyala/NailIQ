import numpy as np

# Rough starting estimate -- no labeled dataset exists yet to calibrate against.
# Positive relative sagitta means the nail-plate contour bows toward the finger
# (concave/scooped); values above this are flagged as outside typical range.
KOILONYCHIA_SAGITTA_THRESHOLD = 0.04


def _nail_plate_segment_indices(n, tip_idx, cuticle_idx, direction):
    indices = []
    idx = cuticle_idx
    for _ in range(n):
        indices.append(idx)
        if idx == tip_idx:
            break
        idx = (idx - direction) % n
    return indices


def measure_nail_curvature(pts, keypoints):
    n = len(pts)
    tip_idx = keypoints["tip_idx"]
    cuticle_idx = keypoints["cuticle_idx"]
    direction = keypoints["direction"]
    B = np.asarray(keypoints["B"], dtype=np.float64)
    C = np.asarray(keypoints["C"], dtype=np.float64)

    indices = _nail_plate_segment_indices(n, tip_idx, cuticle_idx, direction)
    segment = pts[indices].astype(np.float64)

    BC = C - B
    chord_len = np.linalg.norm(BC)
    if chord_len < 1e-6:
        return 0.0

    max_signed_dist = 0.0
    for pt in segment:
        BP = pt - B
        t = np.dot(BP, BC) / (chord_len**2)
        proj = B + t * BC
        dist = np.linalg.norm(pt - proj)
        cross = BC[0] * (pt[1] - B[1]) - BC[1] * (pt[0] - B[0])
        signed_dist = dist if cross > 0 else -dist
        if abs(signed_dist) > abs(max_signed_dist):
            max_signed_dist = signed_dist

    return float(max_signed_dist / chord_len)


def sagitta_to_verdict(relative_sagitta):
    return "outside" if relative_sagitta > KOILONYCHIA_SAGITTA_THRESHOLD else "within"


def build_finding(pts, keypoints, confidence):
    sagitta = measure_nail_curvature(pts, keypoints)
    return {
        "label": "koilonychia",
        "display_name": "Nail curvature (koilonychia)",
        "value": None,
        "unit": None,
        "verdict": sagitta_to_verdict(sagitta),
        "confidence": confidence,
        "track_used": "geometric",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "koilonychia",
        "display_name": "Nail curvature (koilonychia)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "geometric",
        "failure_reason": failure_reason,
    }
