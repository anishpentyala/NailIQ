import json
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.infer.pipeline import analyze as run_analysis, validate_photo  # noqa: E402
from models import ScanRecord, db  # noqa: E402

app = Flask(__name__)
CORS(app)

basedir = os.path.dirname(os.path.abspath(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'nailiq.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all()


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    if "side_image" not in data or "top_image" not in data:
        return jsonify({"error": "missing 'side_image' and/or 'top_image' fields (base64 strings)"}), 400

    # Geometry runs on the side photo; the trained CNN runs on both photos
    # (two separate findings). See ml/infer/pipeline.analyze.
    result = run_analysis(data["side_image"], data["top_image"])

    try:
        db.session.add(ScanRecord(findings_json=json.dumps(result["findings"])))
        db.session.commit()
    except Exception:  # noqa: BLE001 -- history logging must never block a result
        db.session.rollback()

    return jsonify(result)


@app.route("/history", methods=["GET"])
def history():
    records = ScanRecord.query.order_by(ScanRecord.created_at.desc()).all()
    return jsonify({"scans": [r.to_dict() for r in records]})


@app.route("/validate_photo", methods=["POST"])
def validate_photo_route():
    data = request.get_json(silent=True) or {}
    if "image" not in data or "view" not in data:
        return jsonify({"error": "missing 'image' and/or 'view' fields"}), 400

    # The side view needs full keypoints (fingertip + cuticle vertex) since
    # that's what /analyze actually measures. The top-down view isn't shaped
    # like a profile, so it only gets a basic "is there a finger here" check.
    require_keypoints = data["view"] == "side"
    ok, failure_reason = validate_photo(data["image"], require_keypoints=require_keypoints)
    return jsonify({"ok": ok, "failure_reason": failure_reason})


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
