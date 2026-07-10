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
from .preprocessing import crop_to_finger_roi

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
