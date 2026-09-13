"""Repeatability + plausibility gate for the side-profile geometry measurement.

Why this exists (measured 2026-09-12, before keypoints.CURVATURE_STEP_FRAC existed): the
cuticle vertex was the peak of a 3-point discrete curvature on a pixel contour, so on
real photos it was decided by pixel noise. The one real healthy side photo measured
126.6deg as captured, 246.4deg after a JPEG re-save at q65, 230.9deg at 0.8x scale and
164.9deg after a 1px blur -- and /analyze reported 214.3deg "outside" with confidence
0.97 from that same noise. A number that changes verdict when the photo is re-saved is
not a measurement, so it must not produce a verdict.

The gate re-measures the photo under nuisance perturbations that should not change the
anatomy (JPEG re-encode, slight blur, rescale) and only lets the geometry findings
through when:
  1. every perturbed copy still yields valid keypoints,
  2. the clubbing angle's spread across copies is <= MAX_ANGLE_SPREAD_DEG,
  3. every copy gives the same clubbing verdict AND the same koilonychia verdict,
  4. the angle is inside PLAUSIBLE_ANGLE_RANGE_DEG (outside it the keypoints are not on
     the nail fold -- e.g. a top-down photo measured as if it were a side profile gave
     "stable" 237-298deg angles on healthy dataset nails),
  5. the angle is not within CLUBBING_GUARD_BAND_DEG of the 180deg threshold. After the
     scale-relative curvature fix the same healthy photo measured a *stable* 182.6deg:
     stability can't catch a systematic keypoint error, a guard band at least stops a
     near-threshold one from asserting a verdict.
Otherwise the findings are inconclusive with a retake-able failure reason. This is the
methodological substitute for "never wrong": abstain whenever the measurement can't be
reproduced. Regression checks: ml/infer/tests/test_measurement_gate.py and
ml/eval/eval_real_hands.py.
"""
import cv2
import numpy as np

from . import clubbing, koilonychia
from .keypoints import find_keypoints
from .preprocessing import extract_best_contour

# A physiological guard, not a calibrated threshold: normal Lovibond/profile angles sit
# near 160deg and clubbed ones a little above 180deg (Hsu et al. 2024 via clubbing.py);
# values far outside this band mean the keypoints landed somewhere other than the
# nail fold.
PLAUSIBLE_ANGLE_RANGE_DEG = (140.0, 220.0)

# Max allowed max-min angle across perturbed copies. Stable real measurements in the
# 2026-09-12 probe varied by 0.5-6deg; unstable ones by 45-99deg.
MAX_ANGLE_SPREAD_DEG = 10.0

# Guard band around the clubbing threshold (ISO 14253-1-style decision rule): a
# measurement whose tolerated spread could straddle 180deg is not allowed to decide
# either way. Half the tolerated spread, so any accepted angle's whole perturbation
# range stays on one side of the threshold.
CLUBBING_GUARD_BAND_DEG = MAX_ANGLE_SPREAD_DEG / 2


def _perturbations(image):
    for quality in (90, 70):
        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            yield cv2.imdecode(buf, cv2.IMREAD_COLOR)
    yield cv2.GaussianBlur(image, (5, 5), 1.0)
    yield cv2.resize(image, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_AREA)
    yield cv2.resize(image, None, fx=1.25, fy=1.25, interpolation=cv2.INTER_CUBIC)


def _measure(image):
    """(angle, clubbing_verdict, koilonychia_verdict) or None if keypoints fail."""
    contour, validation = extract_best_contour(image)
    if not validation["is_valid"]:
        return None
    kp, kv = find_keypoints(contour, entry_edge=validation.get("primary_edge"),
                            frame_size=validation.get("frame_size"))
    if not kv["is_valid"]:
        return None
    return _summarize(contour, kp)


def _summarize(contour, kp):
    angle = clubbing.measure_nail_angle(kp["A"], kp["B"], kp["C"], kp["cuticle_is_concave"])
    sagitta = koilonychia.measure_nail_curvature(contour, kp)
    return angle, clubbing.angle_to_verdict(angle), koilonychia.sagitta_to_verdict(sagitta)


def check(image, contour, keypoints):
    """Return (failure_reason | None, stability) for keypoints already found on image.

    stability is in [0, 1] (1 = identical across copies) and is used to scale the
    heuristic confidence; it is not a probability.
    """
    base = _summarize(contour, keypoints)
    lo, hi = PLAUSIBLE_ANGLE_RANGE_DEG
    if not lo <= base[0] <= hi:
        return "angle_implausible", 0.0
    if abs(base[0] - clubbing.CLUBBING_ANGLE_THRESHOLD_DEG) < CLUBBING_GUARD_BAND_DEG:
        return "measurement_borderline", 0.0

    runs = [base]
    for perturbed in _perturbations(image):
        m = _measure(perturbed)
        if m is None:
            return "measurement_unstable", 0.0
        runs.append(m)

    angles = np.array([r[0] for r in runs])
    spread = float(angles.max() - angles.min())
    if spread > MAX_ANGLE_SPREAD_DEG:
        return "measurement_unstable", 0.0
    if len({r[1] for r in runs}) > 1 or len({r[2] for r in runs}) > 1:
        return "measurement_unstable", 0.0
    return None, 1.0 - spread / (2 * MAX_ANGLE_SPREAD_DEG)
