import base64
import binascii
import json
import os
import sys
import time
from collections import deque
from threading import Lock

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.infer.pipeline import analyze as run_analysis, validate_photo  # noqa: E402
from models import Feedback, ScanRecord, db  # noqa: E402

app = Flask(__name__)

# allow the frontend to call this API from a different port/domain
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allowed_origins = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]
CORS(app, origins=_allowed_origins)

# don't let a huge request through
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

basedir = os.path.dirname(os.path.abspath(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'nailiq.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all()

# basic rate limit so one person can't spam the analyze endpoint
_RATE_LIMIT = 30          # requests
_RATE_WINDOW = 60.0       # seconds
_rate_hits = {}
_rate_lock = Lock()


def _rate_limited(ip):
    now = time.time()
    with _rate_lock:
        hits = _rate_hits.setdefault(ip, deque())
        while hits and now - hits[0] > _RATE_WINDOW:
            hits.popleft()
        if len(hits) >= _RATE_LIMIT:
            return True
        hits.append(now)
        return False


def _valid_b64_image(value, max_b64_len=10_000_000):
    if not isinstance(value, str) or not (0 < len(value) <= max_b64_len):
        return False
    try:
        base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return False
    return True


@app.before_request
def _enforce_rate_limit():
    if request.method == "POST" and request.path in ("/analyze", "/validate_photo", "/feedback"):
        if _rate_limited(request.remote_addr or "unknown"):
            return jsonify({"error": "rate_limited", "message": "Too many requests; slow down."}), 429
    return None


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    if "side_image" not in data or "top_image" not in data:
        return jsonify({"error": "missing 'side_image' and/or 'top_image' fields (base64 strings)"}), 400
    if not _valid_b64_image(data["side_image"]) or not _valid_b64_image(data["top_image"]):
        return jsonify({"error": "'side_image' and 'top_image' must be valid base64 image strings"}), 400

    result = run_analysis(data["side_image"], data["top_image"])

    try:
        record = ScanRecord(findings_json=json.dumps(result["findings"]))
        db.session.add(record)
        db.session.commit()
        result["scan_id"] = record.id
    except Exception:  # noqa: BLE001
        db.session.rollback()

    return jsonify(result)


_HISTORY_DEFAULT_LIMIT = 100
_HISTORY_MAX_LIMIT = 500


@app.route("/history", methods=["GET"])
def history():
    # cap how many scans we return so the response doesn't get huge
    try:
        limit = int(request.args.get("limit", _HISTORY_DEFAULT_LIMIT))
    except ValueError:
        limit = _HISTORY_DEFAULT_LIMIT
    limit = max(1, min(limit, _HISTORY_MAX_LIMIT))
    records = (
        ScanRecord.query.order_by(ScanRecord.created_at.desc()).limit(limit).all()
    )
    return jsonify({"scans": [r.to_dict() for r in records]})


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json(silent=True) or {}
    label = data.get("label")
    shown_verdict = data.get("shown_verdict")
    agreed = data.get("agreed")
    if not isinstance(label, str) or not label:
        return jsonify({"error": "missing 'label'"}), 400
    if shown_verdict not in ("within", "outside", "inconclusive"):
        return jsonify({"error": "invalid 'shown_verdict'"}), 400
    if not isinstance(agreed, bool):
        return jsonify({"error": "'agreed' must be a boolean"}), 400

    note = data.get("note")
    if note is not None and (not isinstance(note, str) or len(note) > 1000):
        return jsonify({"error": "invalid 'note'"}), 400

    scan_id = data.get("scan_id")
    if scan_id is not None and not isinstance(scan_id, int):
        return jsonify({"error": "invalid 'scan_id'"}), 400

    try:
        fb = Feedback(scan_id=scan_id, label=label, shown_verdict=shown_verdict,
                      agreed=agreed, note=note)
        db.session.add(fb)
        db.session.commit()
        return jsonify({"ok": True, "id": fb.id})
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"ok": False}), 500


@app.route("/validate_photo", methods=["POST"])
def validate_photo_route():
    data = request.get_json(silent=True) or {}
    if "image" not in data or "view" not in data:
        return jsonify({"error": "missing 'image' and/or 'view' fields"}), 400
    if not _valid_b64_image(data["image"]):
        return jsonify({"error": "'image' must be a valid base64 image string"}), 400
    if data["view"] not in ("side", "top"):
        return jsonify({"error": "'view' must be 'side' or 'top'"}), 400

    # side photo needs full keypoint detection, top photo just needs a finger in frame
    require_keypoints = data["view"] == "side"
    ok, failure_reason = validate_photo(data["image"], require_keypoints=require_keypoints)
    return jsonify({"ok": ok, "failure_reason": failure_reason})


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
