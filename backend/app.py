import base64
import binascii
import json
import os
import sys
import time
from collections import deque
from threading import Lock

import re

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.infer.pipeline import analyze as run_analysis, validate_photo, propose_nail_bbox  # noqa: E402
from ml.infer.nail_locator import valid_bbox  # noqa: E402
from ml.infer.color_classifier import model_metadata  # noqa: E402
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
# NAILIQ_DATABASE_URI must be set BEFORE importing this module: Flask-SQLAlchemy 3.x
# builds the engine in init_app below, so changing app.config afterwards is silently
# ignored -- which is how eval scripts and tests that did that wrote to (and the
# endpoint tests' drop_all() could wipe) the real history database.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "NAILIQ_DATABASE_URI", f"sqlite:///{os.path.join(basedir, 'nailiq.db')}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all()
    # databases created before per-browser history have no client_id column; add it in place
    from sqlalchemy import inspect, text
    if "client_id" not in {c["name"] for c in inspect(db.engine).get_columns("scan_record")}:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE scan_record ADD COLUMN client_id VARCHAR(64)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scan_record_client_id ON scan_record (client_id)"))

# Hosted deployment switches (all off by default, so local development is unchanged):
#   NAILIQ_REQUIRE_CLIENT_ID=1  /history returns nothing unless the request carries an X-Client-Id
#   NAILIQ_TRUST_PROXY=1         take the visitor IP from X-Forwarded-For (the host's proxy sits in front)
#   NAILIQ_STATIC_DIR=<dir>      also serve the built web app (frontend/dist) from this server
_REQUIRE_CLIENT_ID = os.environ.get("NAILIQ_REQUIRE_CLIENT_ID") == "1"
_TRUST_PROXY = os.environ.get("NAILIQ_TRUST_PROXY") == "1"
_STATIC_DIR = os.environ.get("NAILIQ_STATIC_DIR")
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def _client_id():
    value = request.headers.get("X-Client-Id", "")
    return value if _CLIENT_ID_RE.match(value) else None


def _visitor_ip():
    if _TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.remote_addr or "unknown"

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
        if _rate_limited(_visitor_ip()):
            return jsonify({"error": "rate_limited", "message": "Too many requests; slow down."}), 429
    return None


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    if "side_image" not in data or "top_image" not in data:
        return jsonify({"error": "missing 'side_image' and/or 'top_image' fields (base64 strings)"}), 400
    if not _valid_b64_image(data["side_image"]) or not _valid_b64_image(data["top_image"]):
        return jsonify({"error": "'side_image' and 'top_image' must be valid base64 image strings"}), 400

    box = data.get('top_nail_bbox')
    if 'top_nail_bbox' in data and not valid_bbox(box):
        return jsonify({'error': 'top_nail_bbox must be [x0,y0,x1,y1] within 0..1'}), 400
    result = (run_analysis(data['side_image'], data['top_image'], top_nail_bbox=box)
              if box is not None else run_analysis(data['side_image'], data['top_image']))

    try:
        record = ScanRecord(findings_json=json.dumps(result["findings"]), client_id=_client_id())
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
    query = ScanRecord.query
    client_id = _client_id()
    if client_id is not None:
        query = query.filter(ScanRecord.client_id == client_id)
    elif _REQUIRE_CLIENT_ID:
        return jsonify({"scans": []})
    records = query.order_by(ScanRecord.created_at.desc()).limit(limit).all()
    return jsonify({"scans": [r.to_dict() for r in records]})


@app.route("/history", methods=["DELETE"])
def clear_history():
    # only ever deletes the caller's own scans; with no valid client id there is nothing that is "theirs"
    client_id = _client_id()
    if client_id is None:
        return jsonify({"error": "missing or invalid X-Client-Id"}), 400
    try:
        deleted = ScanRecord.query.filter(ScanRecord.client_id == client_id).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "could not clear history"}), 500
    return jsonify({"deleted": deleted})


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
    box = data.get('top_nail_bbox')
    if 'top_nail_bbox' in data and (require_keypoints or not valid_bbox(box)):
        return jsonify({'error': 'top_nail_bbox requires top view and valid normalized coordinates'}), 400
    ok, failure_reason = validate_photo(data['image'], require_keypoints=require_keypoints, top_nail_bbox=box)
    proposal = box if box is not None else (propose_nail_bbox(data['image']) if not require_keypoints else None)
    return jsonify({'ok': ok, 'failure_reason': failure_reason, 'top_nail_bbox': proposal,
                    'roi_review_available': 'assisted' in model_metadata().get('validated_roi_modes', [])})


if _STATIC_DIR and os.path.isdir(_STATIC_DIR):
    @app.route("/", defaults={"path": ""}, methods=["GET"])
    @app.route("/<path:path>", methods=["GET"])
    def web_app(path):
        # API routes above are more specific and win; anything else is the built web app
        full = os.path.join(_STATIC_DIR, path)
        if path and os.path.isfile(full):
            return send_from_directory(_STATIC_DIR, path)
        return send_from_directory(_STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
