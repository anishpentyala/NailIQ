"""Offline measurements from reviewed masks; no verdict or production integration."""
import math

import cv2
import numpy as np


def mask(shape, polygons):
    result = np.zeros(shape[:2], dtype=np.uint8)
    h, w = shape[:2]
    for polygon in polygons:
        points = np.asarray(polygon, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3 or not np.isfinite(points).all() or np.any(points < 0) or np.any(points > 1):
            raise ValueError('Polygons require >=3 finite normalized [x,y] points')
        pixels = np.rint(points * [w-1, h-1]).astype(np.int32)
        cv2.fillPoly(result, [pixels], 1)
    return result.astype(bool)


def onycholysis_area(image_shape, nail_polygons, affected_polygons):
    nail = mask(image_shape, nail_polygons)
    affected = mask(image_shape, affected_polygons)
    if not nail.any():
        raise ValueError('Whole-nail mask is empty')
    if np.any(affected & ~nail):
        raise ValueError('Affected annotation extends beyond the nail')
    return {'affected_fraction': float((affected & nail).sum()/nail.sum()),
            'nail_pixels': int(nail.sum()), 'affected_pixels': int(affected.sum()),
            'validated': False, 'verdict': None}


def lindsay_zones(image, nail_polygons, proximal_polygons, distal_polygons):
    nail = mask(image.shape, nail_polygons)
    proximal = mask(image.shape, proximal_polygons)
    distal = mask(image.shape, distal_polygons)
    if not proximal.any() or not distal.any() or np.any(proximal & distal):
        raise ValueError('Zones must be nonempty and nonoverlapping')
    if np.any((proximal | distal) & ~nail):
        raise ValueError('Zones extend beyond the nail')
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(float)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(float)
    p, d = lab[proximal].mean(axis=0), lab[distal].mean(axis=0)
    return {'proximal_fraction': float(proximal.sum()/nail.sum()),
            'distal_fraction': float(distal.sum()/nail.sum()),
            'annotated_coverage': float((proximal|distal).sum()/nail.sum()),
            'lab_zone_distance': float(np.linalg.norm(p-d)),
            'brightness_contrast': float((hsv[...,2][proximal].mean()-hsv[...,2][distal].mean())/255),
            'proximal_saturation': float(hsv[...,1][proximal].mean()/255),
            'within_zone_variance': [float(lab[proximal].var()),float(lab[distal].var())],
            'validated': False, 'verdict': None}
