# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NailIQ: a precautionary screener for nail-based signs of systemic disease
(currently digital clubbing and koilonychia/spoon nails). A user photographs their
finger and gets a finding per condition, each one only ever "within typical range,"
"outside typical range," or "couldn't analyze this photo" — **never** a named
diagnosis. This framing is non-negotiable and must show up on every result screen,
not just a footer disclaimer.

## Commands

### Backend (Flask, in `backend/venv`)
```bash
cd backend
venv\Scripts\activate          # Windows; source venv/bin/activate elsewhere
pip install -r requirements.txt
python app.py                  # runs on :5000 (PORT env var overrides)
```

Run the geometry unit tests (synthetic point sets — no camera, no dataset needed):
```bash
cd backend && venv\Scripts\activate
pytest ../ml/infer/tests/
```
Run a single test: `pytest ../ml/infer/tests/test_geometry.py::test_right_angle_concave`

### Frontend (Vite + React)
```bash
cd frontend
npm install
npm run dev      # :5173
npm run build
npm run lint
```

### Dev servers via Preview
`.claude/launch.json` defines both servers for the `preview_start` MCP tool
(`frontend`, `backend`). Prefer that over manually backgrounding `npm run dev` /
`python app.py` in this repo — it tracks process lifecycle and ports correctly.
Backend's port is configurable via `PORT` env (`autoPort: true` in launch.json) —
this was added after a stale Windows TCP listener got stuck on port 5000.

## Architecture

### Two-photo capture → multi-finding response

The frontend captures **two photos per session** (`CameraCapture.jsx`, internal
step state `'side' | 'top'`): a side-profile shot and a top-down shot. Both are
POSTed to `/analyze` as `{ side_image, top_image }` (base64, no `data:` prefix).
Only `side_image` is analyzed today — `top_image` is decoded and discarded, kept in
the contract on purpose so the capture flow and request shape don't need to change
again when color/texture-based findings (leukonychia, splinter hemorrhages, Terry's
nails — all need a top-down view) get added later.

As of the ML track landing, `/analyze` runs **two tracks**: the geometry track
(clubbing angle + koilonychia sagitta from the side photo) plus a trained-CNN
track (`ml/infer/classifier.py`, MobileNetV3-Small) that classifies *both* photos
as separate findings (`track_used: "ml"`, `label: "ml_side"|"ml_top"`). The ML
track is optional — `classifier.is_available()` gates it, so the geometry response
still works in a torch-free environment. See "The trained-CNN track" below.

The response is always `{ "findings": [...] }`, one entry per condition/track, each
independently `within` / `outside` / `inconclusive`:
```json
{
  "label": "clubbing",
  "display_name": "Nail angle (clubbing)",
  "value": 165.3, "unit": "deg",
  "verdict": "within" | "outside" | "inconclusive",
  "confidence": 0.7,
  "track_used": "geometric",
  "failure_reason": null
}
```
`inconclusive` (with a `failure_reason`) means the CV pipeline couldn't reliably
locate the finger or its keypoints — it never guesses a verdict it isn't confident
in. `confidence` is a heuristic from keypoint-detection quality signals, not a
calibrated probability — don't present it as one in any UI copy.

### Per-photo retake check (`/validate_photo`)

Waiting until both photos are captured and `/analyze` runs to discover a photo had
no detectable finger/nail was a bad user experience, so `CameraCapture.jsx` calls
`POST /validate_photo` (`{ image, view: 'side' | 'top' }` → `{ ok, failure_reason }`)
right after each capture, before advancing to the next step or submitting. On
`ok: false` it shows a retake message (via `failureReasonMessage()` in
`frontend/src/failureReasons.js`) and lets the user retake that same photo without
losing progress on the other one.

`ml/infer/pipeline.py`'s `_extract()` backs both this and `/analyze`: it takes a
`require_keypoints` flag because the side and top photos need different rigor —
`view: 'side'` runs the full fingertip+cuticle keypoint search (same checks
`/analyze` relies on), `view: 'top'` only confirms a finger-shaped contour exists,
since the cuticle-vertex search assumes the side-profile orientation and doesn't
apply to a top-down shot. `validate_photo()` and `analyze_side_profile()` are now
both thin wrappers around `_extract()` — don't reintroduce duplicate
decode/threshold/contour logic in either one.

### `ml/infer/`: a geometry track + a trained-CNN track

The geometry track is classical OpenCV contour analysis — no trained model needed.
MediaPipe Hands was deliberately dropped: it's trained on whole-hand poses, and
this app's photo is a tight single-finger close-up, a framing it wasn't built for.

Pipeline stages, each importable independently:
- `preprocessing.py` — decode base64 → grayscale/threshold/morphology → largest
  contour. Rejects (→ inconclusive) on: no contour, contour too small, or contour
  touching the image border (finger cropped out of frame).
- `keypoints.py` — finds the fingertip (contour extremum + circle-fit prominence
  check) and the cuticle vertex (peak of discrete contour curvature near the tip).
  Also determines `cuticle_is_concave` by comparing the cuticle's curvature sign to
  the fingertip's (the tip is *always* convex regardless of clubbing status, so it's
  a reliable reference). Rejects on keypoints too close together or collinear.
- `clubbing.py` — angle at the cuticle vertex via the cosine rule. **Important**:
  `arccos` alone is mathematically capped at 180°, so a naive implementation can
  never report a clubbed (>180°) angle. The fix is `cuticle_is_concave`: a concave
  cuticle (normal) reports the raw angle; a convex one (clubbed) reports
  `360 - raw_angle`, the reflex angle on the dorsal side. Don't reintroduce a plain
  `arccos`-only formula here.
- `koilonychia.py` — sagitta (max perpendicular distance from the nail-plate
  contour segment to the chord between cuticle and tip), normalized by chord
  length for scale invariance. Sign distinguishes concave/spoon from convex/normal.
- `pipeline.py` — orchestrates all of the above. Both findings share one
  extraction pass; if contour/keypoint detection fails, *both* findings come back
  `inconclusive` with the same `failure_reason` rather than computing one
  condition's geometry on keypoints that weren't validated.

Thresholds (`CLUBBING_ANGLE_THRESHOLD_DEG`, `KOILONYCHIA_SAGITTA_THRESHOLD`, etc.)
are named module-level constants. Koilonychia's in particular is a rough starting
estimate — there's no labeled photo dataset yet to calibrate against.

Adding a third geometric condition: reuse `preprocessing.py` and `keypoints.py`
as-is, add a new `<condition>.py` with `build_finding()`/`inconclusive_finding()`
following the existing pattern, and call it from `pipeline.py`.

### The trained-CNN track (`ml/infer/classifier.py`)

A MobileNetV3-Small (ImageNet transfer learning) classifies a photo as
`clubbing` / `koilonychia` / `healthy`. Trained by `ml/train/train_classifier.py`
on the NailCheck dataset (`data/raw/nailcheck-3xvkl`, downloaded via
`scripts/download_data.py` from Roboflow Universe, CC BY 4.0). Weights live in
`ml/models/nail_classifier.pt` + `nail_classifier_labels.json` (gitignored —
regenerate by re-running training). Test accuracy ~88% on the dataset's held-out
split — **NOT** on real phone photos; treat real-world accuracy as unknown/lower,
and never present it as clinical-grade.

Key facts:
- **Lazy + optional.** torch/torchvision and the weights are only loaded on first
  use; `classifier.is_available()` gates the whole track so `pipeline.analyze()`
  silently omits ML findings (geometry still runs) if torch isn't installed or the
  model isn't trained. Don't make the Flask app hard-depend on torch.
- **Runs on both photos** as two findings (`label: "ml_side"|"ml_top"`). The model
  was trained on top-down/frontal images, so the **side-view ML output is a domain
  mismatch** and weaker than the top-down one — geometry is the authority on the
  side profile. ML findings carry extra fields `predicted_label` and `probs`.
- Verdict mapping: predicted `healthy` → `within`; any condition → `outside`; top
  prob below `CONFIDENCE_THRESHOLD` (0.50) → `inconclusive` (`low_confidence`).
- `pipeline.analyze(side, top)` is the full two-track entry point `/analyze` calls;
  `analyze_side_profile(side)` remains the geometry-only path.

### Frontend component contract

- `CameraCapture.jsx` owns the two-step capture flow internally and only calls
  `onCapture({ sideImage, topImage })` once both shots are taken — `App.jsx` never
  needs to know about the two-step mechanics.
- `ResultView.jsx` renders one finding-card per item in `result.findings`, mapping
  `verdict` through a `COPY` lookup (`within` / `outside` / `inconclusive`) for
  icon/label/message. Any new finding type automatically gets card rendering for
  free as long as it follows the same `{label, display_name, value, unit, verdict,
  confidence, failure_reason}` shape. `track_used: "ml"` findings additionally show
  an "AI model" badge and a "closest visual match" line from `predicted_label`.
- `api.js` is the only place that knows the `/analyze` request/response shape
  (`VITE_API_BASE` env var overrides the default `http://localhost:5000`).

### No persistence yet

There's no database/history endpoint despite `flask-sqlalchemy` being listed in
`backend/requirements.txt` — that's reserved for a planned scan-history feature
(SQLite + a `/history` endpoint + a Recharts angle-over-time view), not yet built.
Don't assume scan results are stored anywhere; each `/analyze` call is stateless.

### Data pipeline

`scripts/download_data.py` pulls nail-image datasets (Roboflow Universe, CC BY 4.0)
into `data/raw/` — needs a free `ROBOFLOW_API_KEY`. `data/raw/nailcheck-3xvkl` is
the classification set the CNN trains on (Clubbing/Koilonychia/Healthy + 5 more
classes, already train/valid/test split). `data/raw/LICENSES.md` (generated) tracks
attribution — CC BY 4.0 requires crediting each source in any submission/README.
`data/raw/` is gitignored (don't commit the images/licensing); re-run the script to
repopulate. The other detection datasets (`nail-clubbing`, etc.) are boxes, not
class folders — not yet wired into training (would need a crop step).
