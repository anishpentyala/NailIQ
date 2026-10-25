"""Entry points for running the whole analysis inside the browser (Pyodide), with no server.

The JavaScript host (frontend/public/ondevice-worker.js) calls analyze()/validate_photo() here. The networks run
in onnxruntime-web, which is asynchronous, but the analysis code is plain synchronous Python. So inference is
replayed: a pass runs the whole analysis, any network call whose result is not cached yet is recorded and answered
with a placeholder, the host then runs the recorded calls in onnxruntime-web and hands the real outputs back with
provide(), and the pass runs again. It stops when a pass needs nothing new, and that last pass used only real
outputs. The analysis is deterministic, so this gives exactly the same answer as a normal call.

The request/response shapes mirror backend/app.py's /analyze and /validate_photo so the web app needs no changes
beyond choosing where to send them.
"""

import base64
import binascii
import hashlib
import json

import numpy as np

from . import onnx_backend

_cache = {}    # key -> logits for a real, already-run network call
_pending = {}  # key -> (onnx name, input batch) recorded by the current pass
_dims = {}


def _key(name, x):
    return f"{name}|{x.shape}|{hashlib.md5(x.tobytes()).hexdigest()}"


def _out_dim(name):
    if name not in _dims:
        from .color_classifier import _LABELS_PATH as color_labels
        from .classifier import _LABELS_PATH as shape_labels
        if name.startswith("nail_color_classifier"):
            _dims[name] = len(json.loads(color_labels.read_text())["classes"])
        elif name.startswith("nail_classifier"):
            _dims[name] = len(json.loads(shape_labels.read_text())["classes"])
        else:
            _dims[name] = 1  # per-sign specialists emit a single logit
    return _dims[name]


def _runner(name, x):
    key = _key(name, x)
    hit = _cache.get(key)
    if hit is not None:
        return hit
    _pending[key] = (name, x.copy())
    return np.zeros((x.shape[0], _out_dim(name)), np.float32)


def configure(model_names):
    """Install the browser runner. model_names: the .onnx files the host can run."""
    onnx_backend.set_runner(_runner, model_names)


def pending():
    """Network calls the last pass needed: [(key, onnx name, shape, raw float32 bytes)]."""
    return [(k, n, list(x.shape), x.astype(np.float32).tobytes()) for k, (n, x) in _pending.items()]


def provide(key, raw, out_cols):
    """Hand back the logits for one recorded call (raw float32 bytes, `out_cols` per row)."""
    if hasattr(raw, "to_py"):  # a JavaScript Uint8Array coming from the browser
        raw = raw.to_py()
    _cache[key] = np.frombuffer(raw, dtype=np.float32).reshape(-1, out_cols).copy()


def reset():
    _cache.clear()
    _pending.clear()


def _valid_b64_image(value, max_b64_len=10_000_000):
    if not isinstance(value, str) or not (0 < len(value) <= max_b64_len):
        return False
    try:
        base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return False
    return True


def _dump(obj):
    return json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def analyze(payload_json):
    """One pass of /analyze. Returns JSON: {"status": int, "body": ..., "needs_inference": bool}."""
    from .nail_locator import valid_bbox
    from . import pipeline

    data = json.loads(payload_json)
    if "side_image" not in data or "top_image" not in data:
        return _dump({"status": 400, "body": {"error": "missing 'side_image' and/or 'top_image' fields"}, "needs_inference": False})
    if not _valid_b64_image(data["side_image"]) or not _valid_b64_image(data["top_image"]):
        return _dump({"status": 400, "body": {"error": "'side_image' and 'top_image' must be valid base64 image strings"}, "needs_inference": False})
    box = data.get("top_nail_bbox")
    if "top_nail_bbox" in data and not valid_bbox(box):
        return _dump({"status": 400, "body": {"error": "top_nail_bbox must be [x0,y0,x1,y1] within 0..1"}, "needs_inference": False})
    _pending.clear()
    try:
        result = (pipeline.analyze(data["side_image"], data["top_image"], top_nail_bbox=box)
                  if box is not None else pipeline.analyze(data["side_image"], data["top_image"]))
    except Exception as exc:  # noqa: BLE001
        if _pending:  # a placeholder output derailed an exploratory pass; run the real calls and go again
            return _dump({"status": 200, "body": None, "needs_inference": True})
        return _dump({"status": 500, "body": {"error": f"analysis failed: {exc}"}, "needs_inference": False})
    return _dump({"status": 200, "body": result, "needs_inference": bool(_pending)})


def validate_photo(payload_json):
    """One pass of /validate_photo."""
    from .nail_locator import valid_bbox
    from .color_classifier import model_metadata
    from . import pipeline

    data = json.loads(payload_json)
    if "image" not in data or "view" not in data:
        return _dump({"status": 400, "body": {"error": "missing 'image' and/or 'view' fields"}, "needs_inference": False})
    if not _valid_b64_image(data["image"]):
        return _dump({"status": 400, "body": {"error": "'image' must be a valid base64 image string"}, "needs_inference": False})
    if data["view"] not in ("side", "top"):
        return _dump({"status": 400, "body": {"error": "'view' must be 'side' or 'top'"}, "needs_inference": False})
    require_keypoints = data["view"] == "side"
    box = data.get("top_nail_bbox")
    if "top_nail_bbox" in data and (require_keypoints or not valid_bbox(box)):
        return _dump({"status": 400, "body": {"error": "top_nail_bbox requires top view and valid normalized coordinates"}, "needs_inference": False})
    _pending.clear()
    ok, failure_reason = pipeline.validate_photo(data["image"], require_keypoints=require_keypoints, top_nail_bbox=box)
    proposal = box if box is not None else (pipeline.propose_nail_bbox(data["image"]) if not require_keypoints else None)
    body = {"ok": ok, "failure_reason": failure_reason, "top_nail_bbox": proposal,
            "roi_review_available": "assisted" in model_metadata().get("validated_roi_modes", [])}
    return _dump({"status": 200, "body": body, "needs_inference": bool(_pending)})
