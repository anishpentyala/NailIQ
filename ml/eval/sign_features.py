"""Research-only colour/spatial features from the existing automatic nail path."""
import cv2
import numpy as np

from ml.infer import image_quality, nail_region, pipeline
from ml.infer.preprocessing import decode_base64_image


def describe(region):
    values, names = [], []

    def add(name, value):
        names.append(name)
        values.append(float(value) if value is not None else float('nan'))

    def stats(name, array):
        finite = np.asarray(array)[np.isfinite(array)]
        for q in (10, 50, 90):
            add(f'{name}_q{q}', np.percentile(finite, q) if finite.size else None)

    for key in ('S', 'V', 'lab_a', 'lab_b'):
        stats(key, region[key])
    for key in ('skin_lab_a', 'skin_lab_b', 'glare_frac'):
        add(key, region[key])
    for key in ('lab_a', 'lab_b'):
        skin = region['skin_' + key]
        add(key + '_skin_difference', np.median(region[key]) - skin if skin is not None else None)
    add('has_skin_reference', region['skin_lab_a'] is not None)
    gv, gs = region['grid_v'], region['grid_s']
    median = np.nanmedian(gv)
    spread = max(float(np.nanpercentile(gv, 90) - np.nanpercentile(gv, 10)), .03)
    zones = []
    for i, (v, s) in enumerate(zip(np.array_split(gv, 8), np.array_split(gs, 8))):
        mask = np.isfinite(v) & np.isfinite(s)
        valid = v[mask]
        zone = np.median(valid) if valid.size else float('nan')
        zones.append(zone)
        add(f'zone{i}_relative_value', (zone - median) / spread)
        stats(f'zone{i}_saturation', s)
        add(f'zone{i}_white_fraction', np.mean((v[mask] > .78) & (s[mask] < .22)) if mask.any() else None)
    for boundary in (4, 5, 6, 7):
        add(f'proximal_distal_contrast_{boundary}',
            (np.nanmean(zones[:boundary]) - np.nanmean(zones[boundary:])) / spread)
    return names, values


def extract(encoded):
    contour, _, reason = pipeline._extract(encoded, require_keypoints=False)
    if reason:
        return None, reason
    image = decode_base64_image(encoded)
    region, reason = nail_region.compute_nail_region(image, contour)
    if reason:
        return None, reason
    names, features = describe(region)
    return {'names': names, 'features': features,
            'skin_ita': region['skin_ita'], 'bbox_norm': list(region['bbox_norm'])}, None


def normalized(values, medians=None, scales=None):
    x = np.asarray(values, dtype=np.float64)
    if medians is None:
        medians = np.array([np.median(col[np.isfinite(col)]) if np.isfinite(col).any() else 0.
                            for col in x.T])
    missing = ~np.isfinite(x)
    x = np.where(missing, medians, x)
    if scales is None:
        scales = np.maximum(np.std(x, axis=0), .01)
    x = np.clip((x - medians) / scales, -10, 10)
    return np.concatenate([x, missing.astype(float)], axis=1).astype(np.float32), medians, scales


def forest_score(model, x):
    votes = model.getVotes(np.asarray(x, dtype=np.float32), 0)
    classes = votes[0].tolist()
    if 1 not in classes:
        raise ValueError('Forest has no positive class')
    return votes[1:, classes.index(1)] / np.maximum(votes[1:].sum(axis=1), 1)
