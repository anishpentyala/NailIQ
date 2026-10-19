"""Estimate a nail-plate region on a top-down finger photo, for the color/texture
track (leukonychia.py + melanonychia.py).

This is the top-down counterpart to keypoints.py: where keypoints.py locates the
side-profile vertices the geometry track measures, this locates the patch of the
top-down photo whose *color* the color track measures. Like the rest of ml/infer
it's classical CV -- no trained model, no dataset.

It is NOT pixel-perfect nail segmentation, and the code is honest about that.
Using PCA on the finger silhouette we take the distal ~45% of the finger length
(the end whose skin is least saturated -- i.e. the nail end) and its central 60%
width, which lands on the nail plate while insetting away from the skin folds at
the sides. Callers treat a too-small / unclear region as inconclusive rather than
guessing a verdict on skin pixels.

compute_nail_region() white-balances the photo first (so absolute color is
comparable across lighting), gates out glare/nail-polish photos, estimates skin
tone (so tone-dependent conditions can adjust), and returns the per-pixel
H/S/V/Lab/position arrays of the nail region plus a rectified grid and a bounding
box for the result overlay. Each condition module computes its own metric from
these (mirroring how clubbing.py and koilonychia.py each derive their own measure
from the shared keypoints).
"""

import cv2
import numpy as np

from . import image_quality

# Below these the region is too small to trust -> inconclusive.
MIN_REGION_PX = 400
# Median Lab chroma (sqrt(a*^2+b*^2)) of the finger mask below which it is a neutral backdrop, not skin.
NEUTRAL_CHROMA_MAX = 3.5
MIN_REGION_FRAC = 0.02

# Distal length fraction taken as nail, and the central width kept (inset from the
# skin folds on either side).
NAIL_LENGTH_FRAC = 0.45
NAIL_WIDTH_FRAC = 0.6

# Rectified nail patch resolution. The region pixels are resampled into this fixed
# grid so texture conditions get a consistent 2D image to work on regardless of the
# photo's size/orientation. Rows run proximal (cuticle, row 0) -> distal (free
# edge, last row); columns run across the nail width. Empty cells are NaN.
GRID_H = 64
GRID_W = 48


def _finger_mask(contour, shape):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [contour.astype(np.int32)], 255)
    return mask


def heuristic_confidence(value, threshold):
    """Modest confidence for a heuristic color verdict: distance past the threshold,
    capped well below the geometry track's (these are uncalibrated estimates)."""
    return round(min(0.65, 0.4 + abs(value - threshold)), 2)


def compute_nail_region(image_bgr, contour, nail_bbox=None):
    """Return (region, reason). region is None and reason set when the nail region
    can't be estimated reliably or the photo is unfit for color analysis
    (nail polish / heavy glare).

    The photo is white-balanced first so absolute color is comparable across
    lighting. region carries the nail pixels' H/S/V (0..1) and CIELab a*/b*, their
    PCA coordinates (across in [-NAIL_WIDTH_FRAC, NAIL_WIDTH_FRAC], along in 0..1),
    a rectified grid (grid_v/grid_s), the skin-tone ITA in degrees (skin_ita, or
    None), and a bounding box (bbox in pixels, bbox_norm in 0..1) for the overlay.
    """
    balanced = image_quality.white_balance(image_bgr)

    finger = _finger_mask(contour, balanced.shape)
    ys, xs = np.nonzero(finger)
    finger_px = int(xs.size)
    if finger_px < MIN_REGION_PX:
        return None, "nail_region_unclear"

    # No-finger guard (2026-10-18): the "finger" contour can be a white/grey backdrop blob (a table, paper),
    # and leukonychia then read "outside" on a photo with no nail in it. Skin and nail of any tone, and a
    # blue finger, carry colour in the raw (un-white-balanced) photo; a finger-sized neutral blob does not.
    if nail_bbox is None:
        _, a_raw, b_raw = image_quality.lab_real(image_bgr)
        chroma = float(np.hypot(np.median(a_raw[ys, xs]), np.median(b_raw[ys, xs])))
        if chroma < NEUTRAL_CHROMA_MAX:
            return None, "nail_region_unclear"

    P = np.stack([xs, ys], axis=1).astype(np.float64)
    mean = P.mean(axis=0)
    Q = P - mean
    cov = (Q.T @ Q) / finger_px
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, int(np.argmax(evals))]  # along the finger
    minor = evecs[:, int(np.argmin(evals))]  # across the finger

    proj_major = Q @ major
    proj_minor = Q @ minor
    span = proj_major.max() - proj_major.min()
    minor_span = np.abs(proj_minor).max()
    if span < 1e-6 or minor_span < 1e-6:
        return None, "nail_region_unclear"

    along = (proj_major - proj_major.min()) / span  # 0..1 along the finger
    across = proj_minor / minor_span                # -1..1 across the finger

    hsv = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV)
    H = hsv[ys, xs, 0].astype(np.float64) / 179.0  # OpenCV hue is 0..179
    S = hsv[ys, xs, 1].astype(np.float64) / 255.0
    V = hsv[ys, xs, 2].astype(np.float64) / 255.0
    L_img, a_img, b_img = image_quality.lab_real(balanced)
    La = L_img[ys, xs]
    aa = a_img[ys, xs]
    ba = b_img[ys, xs]
    # Un-white-balanced b* of the same finger pixels. Cyanosis is a *global* bluish
    # cast, which white_balance is specifically designed to remove -- so measuring it
    # on the balanced image erases the very sign. Every other color condition wants the
    # WB-normalized color (robust to lighting); cyanosis alone reads this raw channel.
    ba_raw = image_quality.lab_real(image_bgr)[2][ys, xs]

    # Decide which end of the finger holds the nail: the nail plate is less
    # saturated than skin, so the lower-saturation end is the nail end.
    lo_end = along < (0.5 - (0.5 - NAIL_LENGTH_FRAC) / 2)  # along < ~0.475
    hi_end = along > (0.5 + (0.5 - NAIL_LENGTH_FRAC) / 2)  # along > ~0.525
    if lo_end.sum() < 1 or hi_end.sum() < 1:
        return None, "nail_region_unclear"
    nail_at_hi = S[hi_end].mean() < S[lo_end].mean()
    nail_along = (along > (1.0 - NAIL_LENGTH_FRAC)) if nail_at_hi else (along < NAIL_LENGTH_FRAC)

    region = nail_along & (np.abs(across) < NAIL_WIDTH_FRAC)
    if nail_bbox is not None:
        from .nail_locator import pixel_box, valid_bbox
        if not valid_bbox(nail_bbox):
            return None, 'invalid_nail_bbox'
        x0, y0, x1, y1 = pixel_box(image_bgr, nail_bbox)
        region = (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
        # A selected distal nail is oriented relative to the visible finger.
        # Tight clinical crops retain the existing saturation-based estimate.
        if region.any():
            relative_position = float(np.median(along[region]) - np.median(along))
            if abs(relative_position) > 0.05:
                nail_at_hi = relative_position > 0
    region_px = int(region.sum())
    if region_px < MIN_REGION_PX or (nail_bbox is None and region_px < MIN_REGION_FRAC * finger_px):
        return None, "nail_region_unclear"

    Hr, Sr, Vr = H[region], S[region], V[region]
    ar_lab, br_lab = aa[region], ba[region]

    # Reject photos where color can't be read off the plate at all.
    quality = image_quality.quality_reason(Vr, Sr)
    if quality:
        return None, quality

    # Skin tone + skin colour from the skin pixels (finger minus the nail region).
    # The skin colour is the per-person reference pallor/cyanosis judge the nail
    # against (an absolute colour threshold can't tell pale-for-this-person apart
    # from simply darker skin).
    skin = ~region
    has_skin = skin.sum() > 200
    skin_ita = image_quality.ita_degrees(La[skin], ba[skin]) if has_skin else None
    skin_lab_a = float(np.median(aa[skin])) if has_skin else None
    skin_lab_b = float(np.median(ba[skin])) if has_skin else None

    ar, cr = along[region], across[region]
    if nail_bbox is not None:
        width = cr.max() - cr.min()
        if width < 1e-6:
            return None, 'nail_region_unclear'
        cr = (cr - cr.min()) / width * (2 * NAIL_WIDTH_FRAC) - NAIL_WIDTH_FRAC
    grid_v, grid_s = _rectify(ar, cr, Vr, Sr, nail_at_hi)

    nx, ny = xs[region], ys[region]
    x0, y0, x1, y1 = int(nx.min()), int(ny.min()), int(nx.max()), int(ny.max())
    h_img, w_img = image_bgr.shape[:2]

    return {
        "H": Hr,
        "S": Sr,
        "V": Vr,
        "lab_a": ar_lab,
        "lab_b": br_lab,
        "across": cr,
        "along": ar,
        "grid_v": grid_v,
        "grid_s": grid_s,
        "skin_ita": skin_ita,
        "skin_lab_a": skin_lab_a,
        "skin_lab_b": skin_lab_b,
        "nail_raw_lab_b": float(np.median(ba_raw[region])),
        "glare_frac": image_quality.glare_fraction(Vr),
        "region_px": region_px,
        "finger_px": finger_px,
        "tip_vec": tuple(float(v) for v in (major if nail_at_hi else -major)),
        "bbox": (x0, y0, x1, y1),
        "bbox_norm": (x0 / w_img, y0 / h_img, x1 / w_img, y1 / h_img),
        'region_source': 'selected_bbox' if nail_bbox is not None else 'finger_estimate',
    }, None


def _rectify(along, across, V, S, nail_at_hi):
    """Resample the region's scattered pixels into a fixed GRID_H x GRID_W patch.

    Rows are oriented proximal (cuticle, row 0) -> distal (free edge, last row) no
    matter which finger end the nail sits on, so texture conditions can rely on a
    stable orientation. Each cell holds the mean V (and S) of the pixels that fall
    in it; cells with no pixels are NaN.
    """
    lo, hi = along.min(), along.max()
    a = (along - lo) / (hi - lo) if hi - lo > 1e-6 else np.zeros_like(along)
    if not nail_at_hi:
        a = 1.0 - a  # row 0 = proximal regardless of which end holds the nail
    c = (across + NAIL_WIDTH_FRAC) / (2 * NAIL_WIDTH_FRAC)

    rows = np.clip((a * GRID_H).astype(int), 0, GRID_H - 1)
    cols = np.clip((c * GRID_W).astype(int), 0, GRID_W - 1)

    sum_v = np.zeros((GRID_H, GRID_W))
    sum_s = np.zeros((GRID_H, GRID_W))
    cnt = np.zeros((GRID_H, GRID_W))
    np.add.at(sum_v, (rows, cols), V)
    np.add.at(sum_s, (rows, cols), S)
    np.add.at(cnt, (rows, cols), 1.0)

    grid_v = np.full((GRID_H, GRID_W), np.nan)
    grid_s = np.full((GRID_H, GRID_W), np.nan)
    nz = cnt > 0
    grid_v[nz] = sum_v[nz] / cnt[nz]
    grid_s[nz] = sum_s[nz] / cnt[nz]
    return grid_v, grid_s
