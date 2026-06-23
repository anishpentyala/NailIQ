import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.infer.pipeline import analyze_side_profile, validate_photo  # noqa: E402

app = Flask(__name__)
CORS(app)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    if "side_image" not in data or "top_image" not in data:
        return jsonify({"error": "missing 'side_image' and/or 'top_image' fields (base64 strings)"}), 400

    # top_image is accepted now and reserved for future color/texture-based
    # findings (leukonychia, splinter hemorrhages, Terry's nails) -- not analyzed yet.
    result = analyze_side_profile(data["side_image"])
    return jsonify(result)


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
