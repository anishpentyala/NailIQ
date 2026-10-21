""""What the AI looked at": a Grad-CAM heatmap overlay for the /analyze response.

Same math as ml/eval/grad_cam.py (that script's job is a batch sanity check
written to disk for a demo/judging artifact; this module is the same technique
wired into the live inference path so a user sees it on their own scan). Lazy +
optional like classifier.py -- gated by is_available(), wrapped so a failure
here can never break the color/geometry findings the rest of /analyze depends on.
"""

import base64

import cv2
import numpy as np

from . import classifier
from .preprocessing import crop_to_finger_roi, finger_roi_box

OVERLAY_SIZE = 256


def is_available():
    return classifier.is_available()


def _heatmap(model, x, target_layer, torch):
    """Grad-CAM for the top predicted class at `target_layer` (an nn.Module).

    Ported as-is from ml/eval/grad_cam.py: hook the target layer's activations
    and gradients, global-average-pool the gradients into per-channel weights,
    and take a weighted, ReLU'd sum of the activations.
    """
    activations, gradients = {}, {}

    def fwd(m, i, o):
        activations["v"] = o

    def bwd(m, gi, go):
        gradients["v"] = go[0]

    h1 = target_layer.register_forward_hook(fwd)
    h2 = target_layer.register_full_backward_hook(bwd)
    try:
        model.zero_grad()
        out = model(x)
        cls = int(out.argmax(1))
        out[0, cls].backward()
        acts = activations["v"][0]
        grads = gradients["v"][0]
        weights = grads.mean(dim=(1, 2))
        cam = torch.relu((weights[:, None, None] * acts).sum(0))
    finally:
        h1.remove()
        h2.remove()
    cam = cam.detach().numpy()
    cam = cam - cam.min()
    cam = cam / (cam.max() + 1e-8)
    return cam


def overlay_b64(image_bgr):
    """Base64 JPEG (no data: prefix) of the ROI crop with a Grad-CAM heatmap
    overlaid, or None if the model/torch isn't available or anything goes wrong.

    Explains the same member classify_bgr() uses as its first vote, on the same
    ROI crop it actually saw -- so the highlighted region matches the prediction
    the user is shown, not a different image or a different ensemble member.
    """
    if not is_available():
        return None
    try:
        from torchvision import transforms

        s = classifier._load()
        torch = s["torch"]
        model = s["members"][0][0]
        target_layer = model.features[-1]

        roi = crop_to_finger_roi(image_bgr)
        rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float() / 255.0
        tf = transforms.Compose([
            transforms.Resize(256, antialias=True),
            transforms.CenterCrop(s["meta"]["img_size"]),
            transforms.Normalize(s["meta"]["mean"], s["meta"]["std"]),
        ])
        x = tf(tensor).unsqueeze(0)

        cam = _heatmap(model, x, target_layer, torch)
        disp = cv2.resize(roi, (OVERLAY_SIZE, OVERLAY_SIZE))
        cam = cv2.resize(cam, (OVERLAY_SIZE, OVERLAY_SIZE))
        heat = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(disp, 0.6, heat, 0.4, 0)

        ok, buf = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            return None
        return base64.b64encode(buf.tobytes()).decode("ascii")
    except Exception:  # noqa: BLE001 -- explanation must never break the response
        return None


MAX_ATTENTION_POINTS = 3
MIN_PEAK_FRAC = 0.6  # a secondary peak must be at least this fraction of the strongest one
PEAK_SEPARATION = 0.2  # minimum distance between peaks, as a fraction of the heat map's side


def cam_peaks_to_image_points(cam, roi_box, image_hw, img_size, k=MAX_ATTENTION_POINTS):
    """Turn a Grad-CAM map into up to `k` attention points in the ORIGINAL photo's normalized coordinates.

    `cam` is the (h, w) heat map over the center-cropped `img_size` square the model saw. That square came from the
    ROI crop (`roi_box`, pixel box in the original photo) after `Resize(256)` on the shorter side + `CenterCrop`,
    so a heat-map cell is mapped back through the same steps. Points are where the model's attention peaked, not
    where any particular sign was found. Returns [{"x", "y", "strength"}], strongest first (strength in 0-1).
    """
    cam = np.asarray(cam, dtype=np.float32)
    if cam.size == 0 or cam.max() <= 0:
        return []
    cam = cv2.GaussianBlur(cam, (0, 0), max(cam.shape) / 24)
    cam = cam / (cam.max() + 1e-8)
    ch, cw = cam.shape
    x0, y0, x1, y1 = roi_box
    rw, rh = x1 - x0, y1 - y0
    s = 256 / min(rw, rh)
    ox = (rw * s - img_size) / 2
    oy = (rh * s - img_size) / 2
    H, W = image_hw

    work = cam.copy()
    points = []
    for _ in range(k):
        iy, ix = np.unravel_index(int(work.argmax()), work.shape)
        peak = float(cam[iy, ix])
        if points and peak < MIN_PEAK_FRAC * points[0]["strength"]:
            break
        if peak <= 0:
            break
        u, v = (ix + 0.5) / cw, (iy + 0.5) / ch
        px = x0 + (ox + u * img_size) / s
        py = y0 + (oy + v * img_size) / s
        points.append({"x": round(float(np.clip(px / W, 0, 1)), 4), "y": round(float(np.clip(py / H, 0, 1)), 4),
                       "strength": round(peak, 3)})
        yy, xx = np.ogrid[:ch, :cw]
        work[((xx - ix) / cw) ** 2 + ((yy - iy) / ch) ** 2 < PEAK_SEPARATION ** 2] = 0
        if work.max() <= 0:
            break
    return points


def attention_points(image_bgr, k=MAX_ATTENTION_POINTS):
    """Attention points (see cam_peaks_to_image_points) for the top photo, or [] if unavailable."""
    if not is_available():
        return []
    try:
        from torchvision import transforms

        s = classifier._load()
        torch = s["torch"]
        model = s["members"][0][0]
        box = finger_roi_box(image_bgr)
        h, w = image_bgr.shape[:2]
        if box is None:
            box = (0, 0, w, h)
        x0, y0, x1, y1 = box
        rgb = cv2.cvtColor(image_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float() / 255.0
        size = s["meta"]["img_size"]
        tf = transforms.Compose([
            transforms.Resize(256, antialias=True),
            transforms.CenterCrop(size),
            transforms.Normalize(s["meta"]["mean"], s["meta"]["std"]),
        ])
        cam = _heatmap(model, tf(tensor).unsqueeze(0), model.features[-1], torch)
        return cam_peaks_to_image_points(cam, box, (h, w), size, k)
    except Exception:  # noqa: BLE001 -- explanation must never break the response
        return []
