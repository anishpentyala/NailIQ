from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    if "image" not in data:
        return jsonify({"error": "missing 'image' field (base64 string)"}), 400

    # Stub: hardcoded response so the frontend loop can be built and tested
    # before the real CV pipeline (Track A/B) exists.
    return jsonify(
        {
            "angle": 165.0,
            "verdict": "within",
            "confidence": 0.0,
            "track_used": "stub",
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
