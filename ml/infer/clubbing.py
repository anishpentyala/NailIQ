import numpy as np

# Normal Lovibond angle is ~160deg; clubbing is >180deg (per Hsu et al. 2024).
CLUBBING_ANGLE_THRESHOLD_DEG = 180.0


def measure_nail_angle(A, B, C, cuticle_is_concave):
    A, B, C = np.asarray(A, dtype=np.float64), np.asarray(B, dtype=np.float64), np.asarray(C, dtype=np.float64)

    BA = A - B
    BC = C - B

    denom = np.linalg.norm(BA) * np.linalg.norm(BC)
    cos_angle = np.dot(BA, BC) / denom if denom > 1e-9 else 0.0
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    raw_angle = float(np.degrees(np.arccos(cos_angle)))

    # arccos alone only ever returns [0, 180]. A concave cuticle notch (normal
    # profile) is genuinely that raw angle, but a convex/bulging cuticle (clubbed
    # profile) is the reflex angle on the dorsal side -- 360 minus the raw value --
    # which is how it exceeds 180 and matches the clinical >180deg definition.
    return raw_angle if cuticle_is_concave else 360.0 - raw_angle


def angle_to_verdict(angle_deg):
    verdict = "outside" if angle_deg > CLUBBING_ANGLE_THRESHOLD_DEG else "within"
    return verdict


def build_finding(A, B, C, cuticle_is_concave, confidence):
    angle = measure_nail_angle(A, B, C, cuticle_is_concave)
    return {
        "label": "clubbing",
        "display_name": "Nail angle (clubbing)",
        "value": round(angle, 1),
        "unit": "deg",
        "verdict": angle_to_verdict(angle),
        "confidence": confidence,
        "track_used": "geometric",
        "failure_reason": None,
    }


def inconclusive_finding(failure_reason):
    return {
        "label": "clubbing",
        "display_name": "Nail angle (clubbing)",
        "value": None,
        "unit": None,
        "verdict": "inconclusive",
        "confidence": 0.0,
        "track_used": "geometric",
        "failure_reason": failure_reason,
    }
