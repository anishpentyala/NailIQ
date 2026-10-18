import numpy as np
import pytest

from ml.infer import orientation


def _img_with_tip(direction):
    im = np.zeros((20, 20, 3), np.uint8)
    r, c = {"D": (18, 10), "U": (1, 10), "L": (10, 1), "R": (10, 18)}[direction]
    im[r, c] = 255
    return im


@pytest.mark.parametrize("d", "DRUL")
def test_rotate_tip_down_puts_marker_at_bottom(d):
    out = orientation.rotate_tip_down(_img_with_tip(d), d)
    r, c = np.argwhere(out[..., 0] == 255)[0]
    assert r >= 17 and 9 <= c <= 11


@pytest.mark.parametrize("vec,d", [((0, 1), "D"), ((0, -1), "U"), ((1, 0.2), "R"), ((-1, -0.3), "L")])
def test_direction_from_vector(vec, d):
    assert orientation.direction_from_vector(*vec) == d
