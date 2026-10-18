import numpy as np
import pytest

from ml.infer.review_measurements import lindsay_zones, mask, onycholysis_area

NAIL = [[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]]
PROXIMAL = [[[.1,.1],[.9,.1],[.9,.45],[.1,.45]]]
DISTAL = [[[.1,.55],[.9,.55],[.9,.9],[.1,.9]]]


def test_affected_area_has_known_fraction_and_never_a_verdict():
    result = onycholysis_area((101,101,3), NAIL, PROXIMAL)
    assert result['affected_fraction'] == pytest.approx(36/81)
    assert result['verdict'] is None and not result['validated']


def test_affected_outside_nail_is_rejected_instead_of_silently_clipped():
    with pytest.raises(ValueError, match='beyond'):
        onycholysis_area((101,101,3), NAIL, [[[0,0],[.5,0],[.5,.5],[0,.5]]])


def test_zone_measurement_tracks_known_brightness_difference():
    image = np.full((101,101,3),80,dtype=np.uint8)
    image[mask(image.shape,PROXIMAL)] = 200
    result = lindsay_zones(image,NAIL,PROXIMAL,DISTAL)
    assert result['brightness_contrast'] == pytest.approx(120/255)
    assert result['verdict'] is None and not result['validated']


def test_overlapping_or_nonfinite_annotations_are_rejected():
    with pytest.raises(ValueError,match='nonoverlapping'):
        lindsay_zones(np.zeros((101,101,3),dtype=np.uint8),NAIL,PROXIMAL,PROXIMAL)
    with pytest.raises(ValueError,match='finite'):
        mask((101,101),[[[0,0],[1,0],[float('nan'),1]]])
