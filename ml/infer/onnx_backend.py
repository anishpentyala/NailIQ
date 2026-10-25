"""Run the shipped networks through ONNX instead of PyTorch (used for on-device inference).

The same Python decision code (ml/infer/*) runs in two places: on the Flask server with PyTorch, and inside
the browser (Pyodide) where PyTorch does not exist. This module is the only thing that differs: it feeds a
preprocessed float32 NCHW batch to an ONNX network and returns raw logits. Preprocessing, temperature scaling,
TTA and softmax are numpy here, mirroring the torchvision transforms the PyTorch path uses.

Off by default. It switches on when either
  * NAILIQ_BACKEND=onnx (native onnxruntime, models in NAILIQ_ONNX_DIR or deploy/ondevice/models) - used by the
    parity tests, or
  * a runner has been installed with set_runner(fn) - the browser installs a JS onnxruntime-web bridge.
"""

import os
from pathlib import Path

import numpy as np

_runner = None
_runner_models = None
_sessions = {}


def _dir():
    default = Path(__file__).resolve().parents[2] / "deploy" / "ondevice" / "models"
    return Path(os.environ.get("NAILIQ_ONNX_DIR", default))


def active():
    return _runner is not None or os.environ.get("NAILIQ_BACKEND") == "onnx"


def set_runner(fn, models=None):
    """fn(name, x) -> logits ndarray; `models` is the set of ONNX file names the host can serve."""
    global _runner, _runner_models
    _runner = fn
    _runner_models = set(models) if models is not None else None


def has(name):
    if _runner is not None:
        return _runner_models is None or name in _runner_models
    return (_dir() / name).is_file()


def run(name, x):
    x = np.ascontiguousarray(x, dtype=np.float32)
    if _runner is not None:
        return np.asarray(_runner(name, x), dtype=np.float32)
    if name not in _sessions:
        import onnxruntime as ort
        _sessions[name] = ort.InferenceSession(str(_dir() / name), providers=["CPUExecutionProvider"])
    return _sessions[name].run(None, {"input": x})[0]


def onnx_name(weights_file):
    return Path(weights_file).with_suffix(".onnx").name


def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def preprocess(rgb, size, mean, std, resize=256):
    """torchvision Resize(resize, antialias) -> CenterCrop(size) -> Normalize, on a uint8 RGB image. -> (3,size,size)."""
    from PIL import Image
    h, w = rgb.shape[:2]
    if resize is not None:
        short, long_ = (w, h) if w <= h else (h, w)
        new_short, new_long = resize, int(resize * long_ / short)
        nw, nh = (new_short, new_long) if w <= h else (new_long, new_short)
        if (nw, nh) != (w, h):
            rgb = np.asarray(Image.fromarray(np.ascontiguousarray(rgb)).resize((nw, nh), Image.BILINEAR))
        h, w = rgb.shape[:2]
        top, left = int(round((h - size) / 2.0)), int(round((w - size) / 2.0))
        rgb = rgb[top:top + size, left:left + size]
    x = rgb.astype(np.float32).transpose(2, 0, 1) / 255.0
    return (x - np.asarray(mean, np.float32)[:, None, None]) / np.asarray(std, np.float32)[:, None, None]


def ensemble_probs(meta, members, rgb):
    """Temperature-scaled softmax averaged over TTA (image + h-flip) and ensemble members.

    members: [(weights_file, temperature)] -> class probability vector.
    """
    base = preprocess(rgb, meta["img_size"], meta["mean"], meta["std"])
    views = np.stack([base, base[:, :, ::-1]])
    total = None
    for weights_file, temperature in members:
        p = softmax(run(onnx_name(weights_file), views) / temperature).mean(axis=0)
        total = p if total is None else total + p
    return total / len(members)
