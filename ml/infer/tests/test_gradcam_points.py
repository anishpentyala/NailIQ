import numpy as np

from ml.infer.gradcam import cam_peaks_to_image_points


def _cam(peaks, n=7, sigma=1.0):
    yy, xx = np.mgrid[:n, :n]
    cam = np.zeros((n, n), np.float32)
    for (y, x, a) in peaks:
        cam += a * np.exp(-(((yy - y) ** 2 + (xx - x) ** 2) / (2 * sigma ** 2)))
    return cam


def test_center_peak_maps_through_roi_crop():
    # 400x400 ROI at (100, 50): scale 256/400, 16px crop offset -> the heat map's center is the ROI's center
    pts = cam_peaks_to_image_points(_cam([(3, 3, 1.0)]), (100, 50, 500, 450), (800, 1000), 224)
    assert len(pts) == 1
    assert abs(pts[0]["x"] - 0.3) < 0.02 and abs(pts[0]["y"] - 0.3125) < 0.02
    assert pts[0]["strength"] == 1.0


def test_secondary_peaks_need_enough_strength_and_separation():
    pts = cam_peaks_to_image_points(_cam([(1, 1, 1.0), (5, 5, 0.8), (1, 5, 0.1)]), (0, 0, 400, 400), (400, 400), 224)
    assert len(pts) == 2  # the 0.1 peak is below the strength floor
    assert pts[0]["strength"] > pts[1]["strength"]
    assert pts[0]["x"] < pts[1]["x"] and pts[0]["y"] < pts[1]["y"]


def test_points_stay_in_unit_square_and_empty_map_gives_none():
    pts = cam_peaks_to_image_points(_cam([(0, 0, 1.0)]), (0, 0, 300, 600), (600, 300), 224)
    assert all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in pts)
    assert cam_peaks_to_image_points(np.zeros((7, 7)), (0, 0, 10, 10), (10, 10), 224) == []
