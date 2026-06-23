"""Grad-CAM sanity check: is the classifier looking at the NAIL or the background?

Overlays a class-activation heatmap on a handful of test images so you can see,
literally, where the model is attending. If the hot region sits on the nail, the
prediction is trustworthy; if it's on the background/skin, the ROI crop and more
data are doing real work and the model still needs help.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/grad_cam.py

Writes overlays to ml/eval/gradcam_out/ (gitignored). Great judging/demo artifact.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision import transforms

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from ml.infer import classifier  # noqa: E402
from ml.infer.preprocessing import crop_to_finger_roi  # noqa: E402

DATA = REPO / "data" / "raw" / "nailcheck-3xvkl" / "test"
OUT = Path(__file__).resolve().parent / "gradcam_out"
SAMPLES_PER_CLASS = 4
FOLDERS = {"Clubbing": "clubbing", "Koilonychia": "koilonychia", "Healthy Nail": "healthy"}


def _heatmap(model, x, target_layer, torch):
    """Grad-CAM for the top predicted class at `target_layer` (an nn.Module)."""
    activations, gradients = {}, {}

    def fwd(m, i, o):
        activations["v"] = o  # returning None: don't replace the layer output

    def bwd(m, gi, go):
        gradients["v"] = go[0]  # returning None: don't replace grad_input

    h1 = target_layer.register_forward_hook(fwd)
    h2 = target_layer.register_full_backward_hook(bwd)
    try:
        model.zero_grad()
        out = model(x)
        cls = int(out.argmax(1))
        out[0, cls].backward()
        acts = activations["v"][0]              # (C, h, w)
        grads = gradients["v"][0]               # (C, h, w)
        weights = grads.mean(dim=(1, 2))        # global-average-pool the gradients
        cam = torch.relu((weights[:, None, None] * acts).sum(0))
    finally:
        h1.remove()
        h2.remove()
    cam = cam.detach().numpy()
    cam = cam - cam.min()
    cam = cam / (cam.max() + 1e-8)
    return cam, cls


def main():
    if not classifier.is_available():
        raise SystemExit("Model not available (train it first / install torch).")
    s = classifier._load()
    model, torch_ = s["model"], s["torch"]
    classes = s["meta"]["classes"]
    target_layer = model.features[-1]          # last conv block of MobileNetV3
    tf = transforms.Compose([
        transforms.Resize(256, antialias=True),
        transforms.CenterCrop(s["meta"]["img_size"]),
        transforms.Normalize(s["meta"]["mean"], s["meta"]["std"]),
    ])
    OUT.mkdir(parents=True, exist_ok=True)

    for folder, label in FOLDERS.items():
        d = DATA / folder
        if not d.is_dir():
            continue
        paths = [p for p in sorted(d.iterdir())
                 if p.suffix.lower() in {".jpg", ".jpeg", ".png"}][:SAMPLES_PER_CLASS]
        for p in paths:
            bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            roi = crop_to_finger_roi(bgr)
            rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            tensor = torch_.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float() / 255.0
            x = tf(tensor).unsqueeze(0)

            cam, cls = _heatmap(model, x, target_layer, torch_)
            disp = cv2.resize(roi, (256, 256))
            cam = cv2.resize(cam, (256, 256))
            heat = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(disp, 0.6, heat, 0.4, 0)
            cv2.putText(overlay, f"true:{label} pred:{classes[cls]}", (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imwrite(str(OUT / f"{label}__{p.stem}.png"), overlay)
            print(f"{label:12s} {p.name:30s} -> pred {classes[cls]}")

    print(f"\nWrote overlays to {OUT}")


if __name__ == "__main__":
    main()
