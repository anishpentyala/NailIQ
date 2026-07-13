"""Evaluate the color/texture track on REAL phone photos -- the number that actually
matters, and the one piece missing from this track's eval suite. `eval_real.py`
already does this for the geometry+CNN track (clubbing/koilonychia); this is its
color-track sibling.

Unlike `eval_color_ensemble.py` (isolated CNN on clean dataset crops) or
`eval_color_sensitivity.py` (dataset photos through the real pipeline, but still
clinical/dataset images), this runs the FULL /analyze path - region detection, bbox
crop, classical heuristic, CNN, and color_fusion - over real phone photos you collect
yourself. That is the only way to find out whether nail_region's finger-silhouette
detection, tuned and tested against dataset photos, actually works on a phone photo
taken by an actual user.

Layout (folder name = true condition or "healthy"; gitignored, personal photos):
    data/real_eval_color/healthy/*.jpg
    data/real_eval_color/leukonychia/*.jpg
    data/real_eval_color/pallor/*.jpg
    ...one folder per condition in ml.infer.color_fusion's covered set, plus healthy.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/eval_real_color.py

HONESTY NOTE: as of this session, data/real_eval_color/ does not exist and this
script has never been run against real photos -- there is no camera/subject
available to generate them autonomously. This is a harness, not a result. The color
track's true phone-photo accuracy remains unmeasured; do not claim otherwise. Even
10-20 labeled real photos per condition (healthy included) would make this
meaningful - the geometry track's eval_real.py needed no more than that.
"""
import base64
import sys
import tempfile
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

import app as app_module  # noqa: E402

_scratch_db = Path(tempfile.gettempdir()) / "nailiq_eval_real_color.db"
app_module.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(_scratch_db).replace("\\", "/")
app_module._rate_limited = lambda ip: False  # test client shares one IP; not a real client
with app_module.app.app_context():
    app_module.db.create_all()
client = app_module.app.test_client()

REAL = REPO / "data" / "real_eval_color"
COLOR_TRACKS = ("color", "color_fused")


def b64(path):
    ok, buf = cv2.imencode(".jpg", cv2.imread(str(path)), [cv2.IMWRITE_JPEG_QUALITY, 92])
    return base64.b64encode(buf.tobytes()).decode()


def main():
    if not REAL.is_dir():
        raise SystemExit(
            f"No real-photo set at {REAL}.\n"
            "Create data/real_eval_color/<condition-or-healthy>/ and drop labeled "
            "real phone photos in (a side photo isn't needed for the color track, "
            "but /analyze requires one -- this script reuses one stock side photo "
            "for every request, which only affects the geometry findings, not color).\n"
            "See this file's docstring for the layout and the honesty note about "
            "why this hasn't been run yet."
        )

    side = b64(sorted((REPO / "data/raw/merged/test/healthy").glob("*.jpg"))[0])

    labels = sorted(d.name for d in REAL.iterdir() if d.is_dir())
    if not labels:
        raise SystemExit(f"{REAL} exists but has no label subfolders yet.")

    total = 0
    results = {}
    for true_label in labels:
        d = REAL / true_label
        detected = missed = rejected = 0
        for p in sorted(d.iterdir()):
            if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            total += 1
            resp = client.post("/analyze", json={"side_image": side, "top_image": b64(p)})
            if resp.status_code != 200:
                rejected += 1
                continue
            findings = [f for f in resp.get_json()["findings"] if f["track_used"] in COLOR_TRACKS]
            if true_label == "healthy":
                # a healthy photo is "correct" if nothing gets flagged "outside"
                if any(f["verdict"] == "outside" for f in findings):
                    missed += 1  # a false positive, tracked as a miss for this row
                elif any(f["verdict"] == "within" for f in findings):
                    detected += 1
                else:
                    rejected += 1
                continue
            matching = [f for f in findings if f["label"] == true_label]
            if not matching:
                rejected += 1
                continue
            v = matching[0]["verdict"]
            if v == "outside":
                detected += 1
            elif v == "within":
                missed += 1
            else:
                rejected += 1
        results[true_label] = (detected, missed, rejected)

    if total == 0:
        raise SystemExit(f"Found no images under {REAL}.")

    print(f"evaluated {total} real photos across {len(labels)} labels\n")
    print(f"{'label':22s} {'correct':>8s} {'wrong':>8s} {'rejected':>9s}")
    for label, (det, miss, rej) in sorted(results.items()):
        n = det + miss + rej
        print(f"{label:22s} {det:>8d} {miss:>8d} {rej:>9d}   (n={n})")


if __name__ == "__main__":
    main()
