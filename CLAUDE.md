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

The response is always `{ "findings": [...] }`, one entry per condition, each
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

### `ml/infer/`: one shared geometry pipeline, multiple findings

This is classical OpenCV contour analysis — **no trained model, no dataset**.
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

### Frontend component contract

- `CameraCapture.jsx` owns the two-step capture flow internally and only calls
  `onCapture({ sideImage, topImage })` once both shots are taken — `App.jsx` never
  needs to know about the two-step mechanics.
- `ResultView.jsx` renders one finding-card per item in `result.findings`, mapping
  `verdict` through a `COPY` lookup (`within` / `outside` / `inconclusive`) for
  icon/label/message. Any new finding type automatically gets card rendering for
  free as long as it follows the same `{label, display_name, value, unit, verdict,
  confidence, failure_reason}` shape.
- `api.js` is the only place that knows the `/analyze` request/response shape
  (`VITE_API_BASE` env var overrides the default `http://localhost:5000`).

### No persistence yet

There's no database/history endpoint despite `flask-sqlalchemy` being listed in
`backend/requirements.txt` — that's reserved for a planned scan-history feature
(SQLite + a `/history` endpoint + a Recharts angle-over-time view), not yet built.
Don't assume scan results are stored anywhere; each `/analyze` call is stateless.

### Data pipeline is unstarted

`data/{positive,negative,augmented,raw}/` exist as gitignored placeholders for a
future trained classifier (e.g. leukonychia/splinter hemorrhages, which need
color/texture rather than pure geometry). No collection/augmentation scripts exist
yet. Don't assume any dataset is present when working in this area.
