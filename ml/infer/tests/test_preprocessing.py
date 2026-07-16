import numpy as np

from ml.infer.preprocessing import is_flat_frame


def test_solid_black_frame_is_flat():
    # A dead/blocked camera feed: no real image content at all.
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    assert is_flat_frame(img)


def test_solid_gray_frame_is_flat():
    img = np.full((240, 320, 3), 128, dtype=np.uint8)
    assert is_flat_frame(img)


def test_noisy_black_frame_is_still_flat():
    # Sensor noise on a dead feed shouldn't be enough to look like real content.
    rng = np.random.default_rng(0)
    img = rng.integers(0, 3, size=(240, 320, 3), dtype=np.uint8)
    assert is_flat_frame(img)


def test_real_scene_is_not_flat():
    # A frame with actual structure (e.g. a hand against a background) has much
    # more grayscale spread than a dead feed.
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    img[60:180, 80:240] = 200
    assert not is_flat_frame(img)
