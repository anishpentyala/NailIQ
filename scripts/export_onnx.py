"""Export every shipped network to ONNX so the app can run its AI on the user's own device.

Writes deploy/ondevice/models/*.onnx plus copies of the small JSON manifests. Each network takes a
normalized float32 NCHW batch (input "input") and returns raw logits ("logits"). Preprocessing,
temperature scaling, TTA and softmax stay in numpy inside ml/infer (see ml/infer/onnx_backend.py), so
the exact same Python decision code runs on the server and in the browser.

Also checks every export against the PyTorch original on a random batch.
Run from the repo root:  ml/venv/Scripts/python.exe scripts/export_onnx.py
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import torch.nn as nn
from torchvision import models

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.infer import classifier, color_classifier  # noqa: E402

MODELS = ROOT / "ml" / "models"
OUT = ROOT / "deploy" / "ondevice" / "models"
SPECIALISTS = ("onycholysis", "leukonychia", "beaus_lines")


def export(model, path, size, tag):
    model.eval()
    dummy = torch.randn(2, 3, size, size)
    torch.onnx.export(model, dummy, str(path), input_names=["input"], output_names=["logits"],
                      dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
                      opset_version=17, dynamo=False)
    # parity: PyTorch vs onnxruntime on a fresh random batch of a different size
    x = (torch.rand(5, 3, size, size) - 0.45) / 0.225  # image-like range
    with torch.no_grad():
        ref = model(x).numpy()
    got = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"]).run(None, {"input": x.numpy()})[0]
    diff = float(np.abs(ref - got).max())
    print(f"{tag:55s} {path.stat().st_size / 1e6:6.1f} MB  max|diff|={diff:.2e}")
    assert diff < 1e-2 * max(1.0, float(np.abs(ref).max())), tag


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    for prefix, module, labels in (("nail_classifier", classifier, "nail_classifier_labels.json"),
                                   ("nail_color_classifier", color_classifier, "nail_color_classifier_labels.json")):
        meta = json.loads((MODELS / labels).read_text())
        for backbone, weights_file, _ in module._members_from_meta(meta):
            net = module._build_backbone(backbone, len(meta["classes"]))
            net.load_state_dict(torch.load(MODELS / weights_file, map_location="cpu"))
            export(net, OUT / weights_file.replace(".pt", ".onnx"), meta["img_size"], weights_file)
        shutil.copy(MODELS / labels, OUT / labels)

    for sign in SPECIALISTS:
        blob = torch.load(MODELS / f"{sign}_specialist.pt", map_location="cpu")
        size = blob.get("size", 224)
        for i, sd in enumerate(blob["state_dicts"]):
            net = models.efficientnet_b0(weights=None)
            net.classifier[1] = nn.Linear(net.classifier[1].in_features, 1)
            net.load_state_dict(sd)
            export(net, OUT / f"{sign}_specialist_{i}.onnx", size, f"{sign}_specialist_{i}")
        manifest = json.loads((MODELS / f"{sign}_specialist.json").read_text())
        manifest.update(size=size, members=len(blob["state_dicts"]))
        (OUT / f"{sign}_specialist.json").write_text(json.dumps(manifest))
    print("total MB:", round(sum(p.stat().st_size for p in OUT.glob("*.onnx")) / 1e6, 1))


if __name__ == "__main__":
    main()
