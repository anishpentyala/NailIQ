import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.infer.pipeline import analyze_side_profile  # noqa: E402

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


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
