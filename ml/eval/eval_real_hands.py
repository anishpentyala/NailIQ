"""Run the real Flask /analyze endpoint over real, un-cropped phone photos of a
whole hand -- the exact framing eval_real.py and every other eval script never
tested, because they all feed pre-cropped clinical dataset images (padded with a
border first; see e.g. eval_color_sensitivity.py's b64()). That gap is how the
border rule and the fingertip-orientation bug shipped unnoticed: a real photo of
your own hand always has the finger entering the frame, and can point any
direction, and nothing here checked either.

Layout (folder name = true label; gitignored, these are personal photos):
    data/real_eval/healthy/<subject>_side.jpg
    data/real_eval/healthy/<subject>_top.jpg
    data/real_eval/clubbing/...

Pairs are matched by stripping the trailing _side/_top suffix, so multiple
subjects/labels can share the folder structure eval_real.py already uses.

Two things are checked per pair:

1. RAW upload path (the exact bytes a real "Upload a photo instead" tap would
   send -- no guide-box crop applied). These photos were captured before the
   guided-capture crop (Stage 3 of the framing fix) existed, so most will
   legitimately fail with `background_not_filling_frame` -- that's the CORRECT,
   honest outcome for an unframed whole-hand photo, not a bug. What this guards
   against is a *silent regression*: if a future change makes the pipeline
   accept one of these and report a verdict, that verdict must never be a
   confident "outside" on a photo labeled healthy -- that's exactly how the
   295-degree false positive shipped.

2. CROPPED path: the same raw pixels, cropped to roughly what Stage 3's guide
   box would have sent (crop bounds recorded in _CROP_OVERRIDES below, tuned by
   hand against these bootstrap photos since they predate the guide-crop
   feature). This is the number that actually demonstrates the fix: a
   correctly-framed real photo should produce plausible, non-crashing findings.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/eval_real_hands.py
"""
import base64
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

_scratch_db = Path(tempfile.gettempdir()) / "nailiq_eval_real_hands.db"
# must be set before importing app (Flask-SQLAlchemy builds the engine at import)
os.environ["NAILIQ_DATABASE_URI"] = "sqlite:///" + str(_scratch_db).replace("\\", "/")
import app as app_module  # noqa: E402

# See CLAUDE.md's rate-limiter trap: the test client shares one IP, and /analyze
# is capped at 30 req/60s, which silently truncates a batch run if not disabled.
app_module._rate_limited = lambda ip: False
with app_module.app.app_context():
    app_module.db.create_all()
client = app_module.app.test_client()

REAL = REPO / "data" / "real_eval"

# Hand-tuned crop boxes (x0, y0, x1, y1) for bootstrap photos captured before the
# guided-capture crop existed. Keyed by "<label>/<subject>_<view>". New photos
# captured through the fixed camera UI won't need an entry here -- they'll
# already be framed correctly by Stage 3's guide box.
_CROP_OVERRIDES = {
    "healthy/anish1_side": (220, 320, 480, 750),
    "healthy/anish1_top": (280, 420, 500, 750),
}

_PAIR_RE = re.compile(r"^(?P<subject>.+)_(?P<view>side|top)\.(jpe?g|png)$", re.IGNORECASE)


def _b64(img_bgr):
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return base64.b64encode(buf.tobytes()).decode()


def _gather_pairs():
    pairs = defaultdict(dict)  # (label, subject) -> {"side": path, "top": path}
    if not REAL.is_dir():
        return pairs
    for label_dir in sorted(REAL.iterdir()):
        if not label_dir.is_dir():
            continue
        for p in sorted(label_dir.iterdir()):
            m = _PAIR_RE.match(p.name)
            if not m:
                continue
            pairs[(label_dir.name, m.group("subject"))][m.group("view").lower()] = p
    return {k: v for k, v in pairs.items() if "side" in v and "top" in v}


def _cropped(path, key):
    img = cv2.imread(str(path))
    box = _CROP_OVERRIDES.get(key)
    if box is None:
        return None
    x0, y0, x1, y1 = box
    return img[y0:y1, x0:x1]


def _report(tag, resp):
    if resp.status_code != 200:
        print(f"    {tag}: HTTP {resp.status_code}")
        return
    findings = resp.get_json()["findings"]
    for f in findings:
        if f["label"] not in ("clubbing", "koilonychia"):
            continue
        print(f"    {tag} {f['label']:12s} {f['verdict']:13s} "
              f"value={f.get('value')} conf={f.get('confidence')} "
              f"fail={f.get('failure_reason')}")


def main():
    pairs = _gather_pairs()
    if not pairs:
        raise SystemExit(
            f"No real hand-photo pairs at {REAL}.\n"
            "Create data/real_eval/<label>/<subject>_side.jpg + <subject>_top.jpg "
            "and drop labeled phone photos in. See this file's docstring."
        )

    false_positives = []
    for (label, subject), views in sorted(pairs.items()):
        print(f"=== {label}/{subject} ===")
        side_img = cv2.imread(str(views["side"]))
        top_img = cv2.imread(str(views["top"]))

        print("  raw (unframed upload path):")
        resp = client.post("/analyze", json={"side_image": _b64(side_img), "top_image": _b64(top_img)})
        _report("raw", resp)
        if resp.status_code == 200 and label == "healthy":
            for f in resp.get_json()["findings"]:
                if f["label"] in ("clubbing", "koilonychia") and f["verdict"] == "outside":
                    false_positives.append((f"{label}/{subject}", "raw", f["label"], f.get("value")))

        side_key = f"{label}/{subject}_side"
        top_key = f"{label}/{subject}_top"
        side_crop = _cropped(views["side"], side_key)
        top_crop = _cropped(views["top"], top_key)
        if side_crop is not None and top_crop is not None:
            print("  cropped (simulated guide-box framing):")
            resp = client.post("/analyze", json={"side_image": _b64(side_crop), "top_image": _b64(top_crop)})
            _report("cropped", resp)
            if resp.status_code == 200 and label == "healthy":
                for f in resp.get_json()["findings"]:
                    if f["label"] in ("clubbing", "koilonychia") and f["verdict"] == "outside":
                        false_positives.append((f"{label}/{subject}", "cropped", f["label"], f.get("value")))
        else:
            print("  cropped: no _CROP_OVERRIDES entry -- add one to test this pair framed")

    print()
    if false_positives:
        print("FALSE POSITIVES on healthy-labeled photos (investigate before shipping):")
        for subject, tag, label, value in false_positives:
            print(f"  {subject} [{tag}] {label} -> outside (value={value})")
    else:
        print("No confident false positives on healthy-labeled photos.")


if __name__ == "__main__":
    main()
