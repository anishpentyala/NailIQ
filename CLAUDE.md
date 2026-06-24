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

Run the geometry unit tests (synthetic point sets — no camera, no dataset needed).
**Run from the repo root, not `backend/`** — the tests import `ml.infer.*`, which
needs the repo root on `sys.path`; running from `backend/` fails with
`ModuleNotFoundError: No module named 'ml'`:
```bash
backend/venv/Scripts/python.exe -m pytest ml/infer/tests/
```
Run a single test:
`backend/venv/Scripts/python.exe -m pytest ml/infer/tests/test_geometry.py::test_right_angle_concave`

### ML training / eval (needs torch + the downloaded dataset; from repo root)
```bash
backend/venv/Scripts/python.exe scripts/download_data.py                # needs ROBOFLOW_API_KEY
backend/venv/Scripts/python.exe scripts/build_classification_dataset.py # merge detection datasets into train
backend/venv/Scripts/python.exe scripts/finalize_merged_eval.py         # restore clean eval split + dedup
backend/venv/Scripts/python.exe ml/train/train_classifier.py --backbone mobilenet_v3_large
backend/venv/Scripts/python.exe ml/train/train_classifier.py --backbone efficientnet_b0  # adds to ensemble
backend/venv/Scripts/python.exe ml/eval/eval_ensemble.py      # ensemble accuracy (what ships)
backend/venv/Scripts/python.exe ml/eval/grad_cam.py           # attention overlays
backend/venv/Scripts/python.exe ml/eval/eval_real.py          # real-photo confusion matrix
```

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

`/analyze` runs **two tracks and fuses them**: the geometry track (clubbing angle
+ koilonychia sagitta from the side photo) and a trained-CNN track
(`ml/infer/classifier.py`, MobileNetV3-Large) that classifies the top-down photo.
`ml/infer/fusion.py` combines them into **one finding per condition**
(`track_used: "fused"`): when both tracks agree the verdict's confidence is
boosted; when they disagree the finding is `inconclusive` (`tracks_disagree`)
rather than asserting a split call. The ML track is optional —
`classifier.is_available()` gates it, so if torch/weights are absent the geometry
findings are returned unchanged (`track_used: "geometric"`). See "The trained-CNN
track" and "Fusing the two tracks" below.

The response is always `{ "findings": [...] }`, one entry per condition, each
independently `within` / `outside` / `inconclusive`. A fused finding adds
`agreement` ("agree" | "geometry_only" | "disagree" | "geometry_unavailable")
plus `geometry` and `ml` sub-objects; a torch-free geometry finding looks like:
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

A **2-model ensemble** (MobileNetV3-Large + EfficientNet-B0, both ImageNet
transfer learning) classifies a photo as `clubbing` / `koilonychia` / `healthy`,
averaging each member's softmax. Trained by `ml/train/train_classifier.py
--backbone <name>`, run once per backbone — each run appends its member to the
ensemble rather than overwriting it. Training data is the **merged** dataset
(`data/raw/merged`): the NailCheck dataset (`data/raw/nailcheck-3xvkl`,
downloaded via `scripts/download_data.py` from Roboflow Universe, CC BY 4.0) plus
two YOLO detection datasets cropped to the nail box and added to *train only* via
`scripts/build_classification_dataset.py`; `scripts/finalize_merged_eval.py`
then restores `merged/valid` and `merged/test` to the original, untouched
NailCheck split (so eval numbers stay comparable to the old baseline) and drops
any train image that's a near-duplicate (dHash, Hamming ≤5) of an eval image to
prevent leakage. Weights live in `ml/models/nail_classifier__<backbone>.pt` +
one shared `nail_classifier_labels.json` (gitignored — regenerate by re-running
training for each backbone). The JSON's `"ensemble"` list carries each member's
`backbone`, `weights_file`, and its own independently-fit calibration
`temperature`; `classifier._members_from_meta()` falls back to the old
single-backbone top-level format if `"ensemble"` is absent, so don't remove that
fallback while any non-ensemble manifest might still be in the wild. Reported
accuracy is on the dataset's held-out split — **NOT** on real phone photos; treat
real-world accuracy as unknown/lower (measure it with `ml/eval/eval_real.py`) and
never present it as clinical-grade.

What makes the prediction more than a raw softmax guess (all in
`classifier.classify_bgr`, mirrored in training so train/inference match):
- **Ensemble.** Two diverse backbones vote and their probabilities are averaged;
  a wrong call from one is usually outvoted by the other. `ml/eval/eval_ensemble.py`
  is the only script that measures this averaged number (what actually ships) —
  `train_classifier.py`'s printed accuracy is each backbone's *solo* number.
- **ROI crop.** `preprocessing.crop_to_finger_roi` crops to the detected finger
  (same contour detector geometry uses) **before** classifying, so the CNN keys on
  the nail, not the background. This is the single biggest real-world robustness
  fix — feeding the whole frame let background clutter swing the prediction.
- **TTA.** Each member's prediction is averaged over the image + its horizontal
  flip, independently, before the cross-member average.
- **Temperature scaling.** Each member's logits are divided by its own
  temperature (fit on the validation set, `fit_temperature` in training) so the
  probability the `CONFIDENCE_THRESHOLD` (0.50) gates on is calibrated, not
  over-confident.

Key facts:
- **Lazy + optional.** torch/torchvision and the weights are only loaded on first
  use; `classifier.is_available()` gates the whole track so `pipeline.analyze()`
  returns the geometry findings unchanged if torch isn't installed or the model
  isn't trained. Don't make the Flask app hard-depend on torch.
- **Top-down photo only.** The model trained on top-down/frontal images, so only
  the top photo is classified for fusion; the side profile is geometry's domain.
  `build_finding` returns extra fields `predicted_label` and `probs`.
- Verdict mapping: predicted `healthy` → `within`; any condition → `outside`; top
  prob below `CONFIDENCE_THRESHOLD` → `inconclusive` (`low_confidence`).
- `pipeline.analyze(side, top)` is the full entry point `/analyze` calls;
  `analyze_side_profile(side)` remains the geometry-only path.

Training (`ml/train/train_classifier.py`) fine-tunes the last few backbone blocks
(not just the head) at a lower LR, with AdamW + cosine LR schedule, EMA weights,
early stopping, class weights + label smoothing for the mild imbalance, and
phone-realistic augmentation (RandAugment, perspective, blur, RandomErasing,
MixUp/CutMix). It prints a confusion matrix + per-class precision/recall for that
one backbone — for a screener, **recall on the condition classes** (don't miss a
real sign) is the metric to watch, but the number that matters for production is
the ensemble's, from `ml/eval/eval_ensemble.py`: **0.935 overall test accuracy**
(n=108), up from 0.898 for the prior single-backbone model on the same split.

### Fusing the two tracks (`ml/infer/fusion.py`)

`fuse(geometry_findings, ml_top_finding)` returns one fused finding per condition.
Per condition C: geometry inconclusive → inconclusive; ML missing / low-confidence
/ predicting the *other* condition → geometry alone stands
(`agreement: "geometry_only"`); tracks agree → agreed verdict with boosted
confidence (`"agree"`); tracks disagree → `inconclusive` (`tracks_disagree`,
`"disagree"`). Only the **top-view** ML signal is used — side-view ML is a domain
mismatch and is deliberately ignored here.

### Eval / diagnostics (`ml/eval/`)

- `grad_cam.py` — Grad-CAM overlays (last conv block) on test images, written to
  `ml/eval/gradcam_out/` (gitignored), to confirm the model attends to the nail,
  not the background. Good judging/demo artifact.
- `eval_real.py` — runs the **full inference path** (ROI + TTA + temperature) over
  real phone photos in `data/real_eval/<label>/` (gitignored, personal images) and
  reports a confusion matrix + per-class recall. This is the number that matters;
  the training split accuracy doesn't reflect phone photos.

### Frontend component contract

- `CameraCapture.jsx` owns the two-step capture flow internally and only calls
  `onCapture({ sideImage, topImage })` once both shots are taken — `App.jsx` never
  needs to know about the two-step mechanics.
- `ResultView.jsx` renders one finding-card per item in `result.findings`, mapping
  `verdict` through a `COPY` lookup (`within` / `outside` / `inconclusive`) for
  icon/label/message. Any new finding type automatically gets card rendering for
  free as long as it follows the same `{label, display_name, value, unit, verdict,
  confidence, failure_reason}` shape. `track_used: "fused"` findings show a
  "Geometry + AI" badge plus an agreement note (from `agreement`) and the model's
  closest visual match (from `ml.predicted_label`); the legacy `track_used: "ml"`
  badge path is still handled for standalone ML findings.
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
