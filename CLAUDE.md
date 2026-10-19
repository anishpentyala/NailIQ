# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NailIQ: a precautionary screener for nail-based signs of systemic disease. It
covers fourteen conditions across four tracks: digital clubbing and koilonychia/spoon
nails (side-profile geometry, fused with a top-down CNN), eleven top-down
color/texture signs - leukonychia, melanonychia, pallor, cyanosis, Terry's nails,
Lindsay's nails, onycholysis, Beau's lines, Muehrcke's lines, splinter hemorrhages,
and pitting - ten of which (all but melanonychia) are further fused with a second
color-condition CNN ensemble, plus onychogryphosis (thickened/overgrown nail), which
is **CNN-only** (no classical measurement exists for it; see "CNN-only conditions"
below). Pallor, Lindsay's nails, Terry's nails and melanonychia
fail the validation bar (or were withheld, see "False-positive reduction" below; Muehrcke's lines too, see "Independent photo-set check") and so show "couldn't analyze this photo" -
see `ml/infer/validation_policy.py`.
A user photographs
their finger and gets a finding per condition, each one only ever "within typical range,"
"outside typical range," or "couldn't analyze this photo" - **never** a named
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

Run the geometry unit tests (synthetic point sets - no camera, no dataset needed).
**Run from the repo root, not `backend/`** - the tests import `ml.infer.*`, which
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
backend/venv/Scripts/python.exe scripts/build_color_classification_dataset.py  # KNM box crops -> color CNN dataset
backend/venv/Scripts/python.exe scripts/build_provenance_manifest.py  # per-image source/license/label CSV (run after the above)
backend/venv/Scripts/python.exe ml/train/train_color_classifier.py --backbone mobilenet_v3_large  # color-condition CNN
backend/venv/Scripts/python.exe ml/train/train_color_classifier.py --backbone efficientnet_b0     # adds to color ensemble
backend/venv/Scripts/python.exe ml/eval/eval_color_ensemble.py  # color ensemble accuracy (what ships)
backend/venv/Scripts/python.exe ml/eval/grad_cam.py           # attention overlays
backend/venv/Scripts/python.exe ml/eval/eval_real.py          # real-photo confusion matrix
backend/venv/Scripts/python.exe ml/eval/eval_end_to_end.py --split valid --cache ml/eval/e2e_valid.json  # color track: recall + FP + abstention via /analyze
backend/venv/Scripts/python.exe ml/eval/tune_color_decision.py --valid ml/eval/e2e_valid.json --test ml/eval/e2e_test.json  # pick decision tables on valid, score on test
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
`python app.py` in this repo - it tracks process lifecycle and ports correctly.
Backend's port is configurable via `PORT` env (`autoPort: true` in launch.json)  -
this was added after a stale Windows TCP listener got stuck on port 5000.

## Architecture

### Two-photo capture → multi-finding response

The frontend captures **two photos per session** (`CameraCapture.jsx`, internal
step state `'side' | 'top'`): a side-profile shot and a top-down shot. Both are
POSTed to `/analyze` as `{ side_image, top_image }` (base64, no `data:` prefix).
**Both photos are now analyzed**: the side photo drives the geometry track, the
top-down photo drives the trained-CNN track and the color/texture track. (The
`top_image` field used to be decoded and discarded - it was kept in the contract on
purpose precisely so the color/texture findings could be added without changing the
capture flow or request shape, which is exactly what happened.)

`/analyze` runs **three tracks**: the geometry track (clubbing angle + koilonychia
sagitta from the side photo), a trained-CNN track (`ml/infer/classifier.py`, a
MobileNetV3-Large + EfficientNet-B0 ensemble) that classifies the top-down photo,
and a color/texture track (`ml/infer/nail_region.py` + one module per condition)
that measures the top-down photo's nail plate.

The geometry and CNN tracks are **fused** by `ml/infer/fusion.py` into **one
finding per geometry condition** (`track_used: "fused"`): when both tracks agree the
verdict's confidence is boosted; when they disagree the finding is `inconclusive`
(`tracks_disagree`) rather than asserting a split call. The CNN track is optional  -
`classifier.is_available()` gates it, so if torch/weights are absent the geometry
findings are returned unchanged (`track_used: "geometric"`). The color/texture track
is **standalone** (`track_used: "color"`), classical CV that needs no trained model,
so it always runs and appends its findings after the geometry/fused ones. See "The
trained-CNN track", "Fusing the two tracks", and "The color/texture track" below.

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
locate the finger or its keypoints - it never guesses a verdict it isn't confident
in. `confidence` is a heuristic from keypoint-detection quality signals, not a
calibrated probability - don't present it as one in any UI copy.

### Per-photo retake check (`/validate_photo`)

Waiting until both photos are captured and `/analyze` runs to discover a photo had
no detectable finger/nail was a bad user experience, so `CameraCapture.jsx` calls
`POST /validate_photo` (`{ image, view: 'side' | 'top' }` → `{ ok, failure_reason }`)
right after each capture, before advancing to the next step or submitting. On
`ok: false` it shows a retake message (via `failureReasonMessage()` in
`frontend/src/failureReasons.js`) and lets the user retake that same photo without
losing progress on the other one.

`ml/infer/pipeline.py`'s `_extract()` backs both this and `/analyze`: it takes a
`require_keypoints` flag because the side and top photos need different rigor  -
`view: 'side'` runs the full fingertip+cuticle keypoint search (same checks
`/analyze` relies on), `view: 'top'` only confirms a finger-shaped contour exists,
since the cuticle-vertex search assumes the side-profile orientation and doesn't
apply to a top-down shot. `validate_photo()` and `analyze_side_profile()` are now
both thin wrappers around `_extract()` - don't reintroduce duplicate
decode/threshold/contour logic in either one.

### `ml/infer/`: a geometry track + a trained-CNN track

The geometry track is classical OpenCV contour analysis - no trained model needed.
MediaPipe Hands was deliberately dropped: it's trained on whole-hand poses, and
this app's photo is a tight single-finger close-up, a framing it wasn't built for.

Pipeline stages, each importable independently:
- `preprocessing.py` - decode base64 → grayscale/threshold/morphology → largest
  contour. Rejects (→ inconclusive) on: no contour, contour too small, or the
  contour touching **3+ frame edges** (`background_not_filling_frame` -
  the plain backdrop doesn't fill the frame, so whatever's beyond it merged into
  the foreground blob; genuinely unanalyzable). **Touching 1-2 edges is normal
  and expected**, not a rejection reason: a real photo of your own hand always
  has the finger entering the frame somewhere, since your hand continues off-frame.
  The validation dict on success carries `border_edges` (which edges, if any, the
  contour touches) and `primary_edge` (the dominant one, by contour-point count,
  when two are touched at a corner) - `pipeline._extract` threads these into
  `find_keypoints` as `entry_edge`. This replaced an earlier all-or-nothing "any
  border contact is a cropped fingertip" rule that rejected every realistically-framed
  real photo while every padded, pre-cropped dataset/eval image (which never touches
  an edge) sailed through unnoticed - see "Real-photo framing" below for how this
  was found and fixed.
- `keypoints.py` - finds the fingertip and the cuticle vertex (peak of discrete
  contour curvature near the tip). `find_fingertip(pts, entry_edge=None)`:
  with an `entry_edge` (the hand entering the frame at a known border),
  the tip is the extremum **farthest from that edge** - `entry_edge=None` (no
  border contact, e.g. every padded dataset/eval image) falls back to the
  original `argmax(y)` rule byte-for-byte, so dataset accuracy can't move.
  `find_keypoints` also rejects (`fingertip_cropped`) when the *selected* tip
  still sits within `TIP_BORDER_MARGIN_PX` of any edge even after picking the
  farthest extremum - a genuinely cropped fingertip, as opposed to normal framing.
  Once the tip is right, `cuticle_is_concave` (comparing the cuticle's curvature
  sign to the fingertip's - the tip is *always* convex regardless of clubbing
  status, so it's a reliable reference) is orientation-free and unchanged.
  Rejects on keypoints too close together or collinear.
- `clubbing.py` - angle at the cuticle vertex via the cosine rule. **Important**:
  `arccos` alone is mathematically capped at 180°, so a naive implementation can
  never report a clubbed (>180°) angle. The fix is `cuticle_is_concave`: a concave
  cuticle (normal) reports the raw angle; a convex one (clubbed) reports
  `360 - raw_angle`, the reflex angle on the dorsal side. Don't reintroduce a plain
  `arccos`-only formula here.
- `koilonychia.py` - sagitta (max perpendicular distance from the nail-plate
  contour segment to the chord between cuticle and tip), normalized by chord
  length for scale invariance. Sign distinguishes concave/spoon from convex/normal.
- `pipeline.py` - orchestrates all of the above. Both findings share one
  extraction pass; if contour/keypoint detection fails, *both* findings come back
  `inconclusive` with the same `failure_reason` rather than computing one
  condition's geometry on keypoints that weren't validated.

Thresholds (`CLUBBING_ANGLE_THRESHOLD_DEG`, `KOILONYCHIA_SAGITTA_THRESHOLD`, etc.)
are named module-level constants. Koilonychia's in particular is a rough starting
estimate - there's no labeled photo dataset yet to calibrate against.

Adding a third geometric condition: reuse `preprocessing.py` and `keypoints.py`
as-is, add a new `<condition>.py` with `build_finding()`/`inconclusive_finding()`
following the existing pattern, and call it from `pipeline.py`.

**Real-photo framing (found and fixed 2026-07-20).** Every eval/test up to this
point fed pre-cropped clinical dataset images, most of them explicitly padded
with a border by the eval script itself before being sent through (e.g.
`eval_color_sensitivity.py`'s `b64()`) - so nothing ever exercised what a real
phone photo of a whole hand actually looks like to this pipeline. The first two
real photos run through `/analyze` came back with **all thirteen findings
inconclusive**, and forcing them through anyway produced a confident false
positive: clubbing at 294.7-308.8°, "outside typical range", confidence
0.97-1.0, on a healthy nail (physically implausible - real angles run ~160°
normal, >180° clubbed). Two compounding bugs, both now fixed (see above):
1. The border rule rejected *any* border contact, but a photo of your own hand
   always has the finger entering the frame at an edge - only 3+ edges touched
   (background not filling the frame) is genuinely unanalyzable.
2. `find_fingertip` assumed the tip is always the bottommost contour point
   (`argmax(y)`), true for the dataset's fixed downward orientation but wrong
   for a real held-up finger (tip at the *top*) - it silently picked the wrong
   end, inverting `cuticle_is_concave` and triggering `clubbing.py`'s `360 -
   raw_angle` reflex branch.

The frontend's capture flow also changed: `CameraCapture.jsx` now crops to the
on-screen guide box (`frontend/src/cameraGuide.js`) before sending, instead of
sending the full video frame - both tracks need a tight single-finger
silhouette, not a whole-hand photo (a whole-hand contour confuses
`nail_region.py`'s distal-45%-of-length nail estimate the same way it confuses
keypoint detection). The crop is **deliberately asymmetric**: generous margin
on the left/right/top of the guide box, but the bottom is never padded away -
it always extends to the raw frame edge. This was empirically necessary, not a
guess: a symmetric padded crop (tested first) puts the contour's border contact
at zero, which reproduces the *same* orientation bug via the `entry_edge=None`
fallback, since the whole point of the fix is reading the entry edge from where
the contour touches a border. The "Upload a photo instead" path has no guide box
to crop to and still sends the full image, which is why the CV-level fix (not
just the UI change) is load-bearing.

`ml/eval/eval_real_hands.py` is the regression harness for this class of bug -
it runs real, uncropped phone photos (`data/real_eval/<label>/<subject>_side.jpg`
+ `_top.jpg`, gitignored personal photos) through the actual Flask `/analyze`
endpoint and flags any confident "outside" verdict on a photo labeled healthy.
Re-run it after touching `preprocessing.py`, `keypoints.py`, or the capture crop.

**The framing fix did not fix real photos - the measurement gate does (2026-09-12).**
Re-running `eval_real_hands.py` after the framing fix still gave clubbing 214.3°,
"outside", confidence 0.97 on the healthy photo. Root cause: the cuticle vertex was
the peak of a 3-point discrete curvature, i.e. pixel noise - the same photo measured
126.6° as captured, 246.4° after a JPEG re-save, 230.9° at 0.8x scale, and the
"cuticle" landed on the finger pad / knuckle crease, never the nail fold. Two fixes:
- `keypoints.CURVATURE_STEP_FRAC`: the curvature neighbourhood scales with contour
  length (min 3 points, so small synthetic test contours are unchanged). Rasterized
  synthetic fingers went from 5/12 to 12/12 verdict-stable under rescaling.
- `ml/infer/measurement_gate.py`, called from `pipeline._extract` (so `/validate_photo`
  asks for a retake too): re-measures under JPEG re-encode / blur / 0.8x / 1.25x and
  returns inconclusive unless every copy agrees on both verdicts with angle spread
  <= 10° (`measurement_unstable`), the angle is physiologically plausible, 140-220°
  (`angle_implausible` - top-down photos gave "stable" 237-298° on healthy nails), and
  it is not within 5° of 180° (`measurement_borderline`, a guard band; after the
  step fix the healthy photo measured a *stable* 182.6°, a systematic keypoint error
  stability alone can't catch).
Net effect: the healthy photo is now inconclusive, not a false positive. **Geometry is
still unvalidated** - there is no labeled side-profile photo set at all, so the gate
makes it abstain rather than making it accurate. Labeled lateral photos are the
blocker. Two ideas were tried and rejected, don't redo them without new data:
- *CNN-only clubbing verdict when geometry abstains*: the shape CNN's clubbing calls at
  >=0.9 were 43/43 correct on valid, yet it called the healthy phone photo clubbing at
  0.938 (raw) / 0.626 (guide crop). Dataset precision does not transfer to phone photos,
  so fusion still requires geometry.
- *Mahalanobis out-of-distribution gate* on the ensembles' penultimate features (fit on
  train, 95% valid quantile; test pass-rate 95.4% so it generalized): it rated that same
  phone photo *in* distribution, so it cost 5% coverage for no protection. Reverted.

### The trained-CNN track (`ml/infer/classifier.py`)

A **2-model ensemble** (MobileNetV3-Large + EfficientNet-B0, both ImageNet
transfer learning) classifies a photo as `clubbing` / `koilonychia` / `healthy`,
averaging each member's softmax. Trained by `ml/train/train_classifier.py
--backbone <name>`, run once per backbone - each run appends its member to the
ensemble rather than overwriting it. Training data is the **merged** dataset
(`data/raw/merged`): the NailCheck dataset (`data/raw/nailcheck-3xvkl`,
downloaded via `scripts/download_data.py` from Roboflow Universe, CC BY 4.0) plus
two YOLO detection datasets cropped to the nail box and added to *train only* via
`scripts/build_classification_dataset.py`; `scripts/finalize_merged_eval.py`
then restores `merged/valid` and `merged/test` to the original, untouched
NailCheck split (so eval numbers stay comparable to the old baseline) and drops
any train image that's a near-duplicate (dHash, Hamming ≤5) of an eval image to
prevent leakage. Weights live in `ml/models/nail_classifier__<backbone>.pt` +
one shared `nail_classifier_labels.json` (gitignored - regenerate by re-running
training for each backbone). The JSON's `"ensemble"` list carries each member's
`backbone`, `weights_file`, and its own independently-fit calibration
`temperature`; `classifier._members_from_meta()` falls back to the old
single-backbone top-level format if `"ensemble"` is absent, so don't remove that
fallback while any non-ensemble manifest might still be in the wild. Reported
accuracy is on the dataset's held-out split - **NOT** on real phone photos; treat
real-world accuracy as unknown/lower (measure it with `ml/eval/eval_real.py`) and
never present it as clinical-grade.

What makes the prediction more than a raw softmax guess (all in
`classifier.classify_bgr`, mirrored in training so train/inference match):
- **Ensemble.** Two diverse backbones vote and their probabilities are averaged;
  a wrong call from one is usually outvoted by the other. `ml/eval/eval_ensemble.py`
  is the only script that measures this averaged number (what actually ships)  -
  `train_classifier.py`'s printed accuracy is each backbone's *solo* number.
- **ROI crop.** `preprocessing.crop_to_finger_roi` crops to the detected finger
  (same contour detector geometry uses) **before** classifying, so the CNN keys on
  the nail, not the background. This is the single biggest real-world robustness
  fix - feeding the whole frame let background clutter swing the prediction.
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
one backbone - for a screener, **recall on the condition classes** (don't miss a
real sign) is the metric to watch, but the number that matters for production is
the ensemble's, from `ml/eval/eval_ensemble.py`: **0.935 overall test accuracy**
(n=108), up from 0.898 for the prior single-backbone model on the same split.

### Fusing the two tracks (`ml/infer/fusion.py`)

`fuse(geometry_findings, ml_top_finding)` returns one fused finding per condition.
Per condition C: geometry inconclusive → inconclusive; ML missing / low-confidence
/ predicting the *other* condition → geometry alone stands
(`agreement: "geometry_only"`); tracks agree → agreed verdict with boosted
confidence (`"agree"`); tracks disagree → `inconclusive` (`tracks_disagree`,
`"disagree"`). Only the **top-view** ML signal is used - side-view ML is a domain
mismatch and is deliberately ignored here.

### The color/texture track (`ml/infer/nail_region.py` + per-condition modules)

A third track, parallel to geometry, that reads the **top-down** photo's nail plate
and reports six color/texture conditions. It's **classical CV** like the geometry
track - no trained model, no dataset needed - so it always runs (even torch-free) and
its findings carry `track_used: "color"`. When the **color-condition CNN** is trained
and torch is present, five of these conditions are instead fused with it into
`track_used: "color_fused"` findings (see "The color-condition CNN track" below); the
rest stay standalone `"color"`. All are appended after the geometry/fused ones in
`pipeline.analyze`.

`nail_region.compute_nail_region(image, contour)` is the shared front-end (the
top-down counterpart to `keypoints.py`). It does **not** do pixel-perfect nail
segmentation - honestly, there's no model for that here. Using PCA on the finger
silhouette it takes the distal ~45% of the finger length (the end whose skin is
*least saturated* - i.e. the nail end) and its central 60% width, which lands on the
nail plate while insetting away from the skin folds. It returns the region's
per-pixel `S`/`V`/`across`/`along` arrays **and** a rectified `grid_v`/`grid_s`
patch (`GRID_H`×`GRID_W`, rows proximal→distal, cols across, NaN where empty) so the
texture conditions get a stable 2D image regardless of photo size/orientation. Too
small / unclear a region → `nail_region_unclear`, and *all* color findings come back
`inconclusive` rather than measuring color on pixels that weren't reliably located.

Each condition is one module with `build_finding(region)` / `inconclusive_finding(reason)`
(same finding shape as geometry), registered in `pipeline._COLOR_CONDITIONS` (which
drives both the findings and the inconclusive list - add a condition there once):
- `leukonychia.py` - fraction of the nail region that's white (high V, low S),
  excluding the very brightest pixels as specular glare.
- `melanonychia.py` - a dark *longitudinal* band: an internal across-bin much
  darker than the rest of the plate (edge bins excluded as edge shadow).
- `terrys_nails.py` - proximal plate mostly opaque-white **and** a darker distal
  band (both gates must trip).
- `beaus_lines.py` - a dark *transverse* groove: an internal `grid_v` row,
  spanning the width, well below the baseline of interior rows.
- `splinter_hemorrhages.py` - small vertically-elongated dark streaks
  (cv2 connected components on a dark mask); needs ≥2 to flag.
- `pitting.py` - multiple small roundish dark pits (same CC approach); needs ≥4.

Every threshold here is a **rough starting estimate** (named module-level constant)
 - there's no labeled photo dataset to calibrate against yet, confidences are capped
modestly via `nail_region.heuristic_confidence`, and the conditions lean toward
`within`/`inconclusive` to limit false positives. Adding a seventh color condition:
add `<condition>.py` following the pattern, build its metric off the `region` dict
(reuse `grid_v`/`grid_s` for texture), and add it to `_COLOR_CONDITIONS`.

**Skin-tone coverage gating (`ml/infer/skin_tone.py`).** `ml/eval/audit_skin_tone.py`
runs the production nail-region path over the datasets and bins each photo's ITA
(`skin_ita`) into tone bands; it found coverage heavily skewed to light skin (of the
~430 images where a skin region is even measurable, ~59% are the lightest band, darker
bands thin/noisy). So the color findings are **largely unvalidated on darker tones**.
Rather than fake a per-tone calibration, `skin_tone.apply_coverage` classifies each
scan's tone into a coverage tier (`well`/`limited`/`minimal`) and, on under-represented
tones, **caps each color finding's confidence and attaches a `tone_caveat` +
`skin_tone_band`** the UI surfaces (`ResultView.jsx`, `.result-tone-caveat`); the
response overlay also carries a `skin_tone` summary. `well`/unmeasurable tones pass
through untouched, and the cap only ever lowers confidence. Re-derive the band→tier
table in `skin_tone.py` from the audit if the dataset grows.

### The color-condition CNN track (`ml/infer/color_classifier.py` + `color_fusion.py`)

The classical color heuristics above are uncalibrated, and calibration on real labeled
photos (`ml/eval/calibrate_color.py`) showed most separate positive from negative only
a little better than chance. So there's a **second, independent CNN ensemble** (separate
from the geometry `classifier.py`) that gives those heuristics a data-backed second
opinion, trained on the data that was already on disk: the KNM dataset's labeled boxes.

Pipeline:
- `scripts/build_color_classification_dataset.py` crops every KNM box to its nail plate
  (15% pad) into `data/raw/color_cls/{train,valid,test}/<slug>/`, keeping KNM's own
  clean image-level split (no reshuffle, no leakage). It trains on **all 10 KNM classes
  with data** (Lindsay's, 2 boxes, excluded) - including `melanoma`, `onychogryphosis`,
  `clubbing`, `koilonychia`, which the app does **not** report - purely so the model
  discriminates instead of forcing every nail into one of the five reported classes.
  Note: box crops here are the *opposite* of `build_color_eval_set.py`'s full images  -
  the classical pipeline needs a whole finger silhouette, a CNN wants the tight nail crop.
  It **also** ingests the Ghana fingernail-anemia set (`data/raw/fingernails-ghana-anemia`,
  a darker-skinned cohort; see `data/DATASETS_DIVERSITY.md`): anemic crops → a new
  `pallor` class (which the heuristic track couldn't calibrate and the CNN didn't cover),
  non-anemic → darker-cohort `healthy`. These are split **patient-grouped** (by finger id,
  not image) so no subject straddles splits. This is the fix for the light-skin skew
  `ml/eval/audit_skin_tone.py` found - it broadens tone exposure and backs `pallor` with
  data. `discover_classes()` picks up `pallor` automatically once the data is on disk;
  retrain both backbones to make it a live signal.
- `ml/train/train_color_classifier.py --backbone <name>` reuses the geometry trainer's
  generic machinery (`train_classifier.py`'s EMA, MixUp/CutMix, temperature scaling, etc.)
  but with these classes and **no ROI re-crop** (inputs are already nail crops). Writes
  `ml/models/nail_color_classifier__<backbone>.pt` + a separate manifest
  `nail_color_classifier_labels.json` (with an `app_conditions` list). Reports overall
  accuracy *and* accuracy restricted to the app's conditions + healthy.
- `ml/infer/color_classifier.py` - lazy + optional, same contract as `classifier.py`
  (`is_available()` gates it). At inference it crops to **nail_region's detected bbox**
  (the closest analogue to the training nail-box crop) and classifies; below
  `CONFIDENCE_THRESHOLD` (0.45) it returns "no opinion." `CLASS_CONFIDENCE_THRESHOLD`
  overrides that floor per class: `pallor` 0.45, `leukonychia` 0.45, `onycholysis`
  0.70, `splinter_hemorrhages` 0.45, `lindsays_nails` 0.40. There is deliberately no
  `melanonychia` entry - see below, its CNN coverage was removed for a licensing
  reason, not a threshold one. Chosen by `ml/eval/sweep_color_thresholds.py`, which
  selects each cutoff on the **valid** split and reports precision/recall on **test**
  only - an earlier version of this file swept and reported on the same test split
  (cutoff-selection leakage), which overstated every number in the old code comments.
  `pallor` is a deliberate override of that script's own pick (0.70): end-to-end
  sensitivity testing (`eval_color_sensitivity.py`) showed 0.70 cost real recall (real
  anemic photos caught only ~20-28% of the time) for no measured false-positive
  benefit, so it's pinned to 0.45 instead (76.2% end-to-end recall, same 0.9%
  false-positive rate) - **the isolated CNN-test sweep is a starting point, not the
  final word; always re-check with `eval_color_sensitivity.py` + a false-positive
  check before trusting a picked cutoff.** Re-sweep whenever the dataset OR the
  training weighting scheme changes.
- `ml/infer/color_fusion.py` - fuses the CNN with the classical findings for **ten
  app conditions**: cyanosis, terrys_nails, beaus_lines, muehrckes_lines, pitting
  (from KNM), pallor (Ghana fingernail-anemia set + the `anemia` Roboflow set's
  `anemic_nail` class as of 2026-09-16, see `data/DATASETS_DIVERSITY.md`),
  splinter_hemorrhages (from the chaa Roboflow set as of 2026-09, see "Dataset
  contamination" below - previously from `nail-disease`, added because as a pure
  heuristic it false-positived badly on healthy nails), and leukonychia/onycholysis/
  lindsays_nails (restored as of 2026-09-16 via the independently-audited `nihati`
  Roboflow set, after losing their only CNN source when `nail-disease` was removed -
  see "Dataset contamination" below). All three are still in `LOW_SAMPLE_CONDITIONS`
  (below) because NIHATI's eval-positive counts for them are tiny (n=4-6) - restoring
  the CNN class did not clear `validation_policy.py`'s bar, see that file.
  **melanonychia is deliberately NOT in this list** - it was
  briefly CNN-covered via `data/raw/nail-dataset-arthitaya` (the only dataset found
  anywhere with this label), then that data source was **removed** from
  `scripts/build_color_classification_dataset.py` once its Kaggle license turned out
  to be a real, unresolved "Unknown" (see `data/raw/LICENSES.md`) rather than a
  formality - training on it and shipping/redistributing the resulting weights was a
  legal risk, not a hypothetical one, so melanonychia went back to classical-heuristic-
  only (`ml/infer/melanonychia.py`, `track_used: "color"`). Not every color condition
  the app reports has CNN coverage, and closing that gap needs a differently-licensed
  data source, not a code change.
  **Deliberately different trust model from `fusion.py`:** geometry is a real measurement
  so it's the authority there; here the heuristic is near-chance, so the **CNN is primary**
  - when it has a confident call it sets the verdict, and the heuristic can only
  corroborate (boost confidence on `agreement: "agree"`), never veto. CNN with no
  confident call → heuristic stands (`"color_only"`); CNN disagrees → CNN leads
  (`"ml_primary"`). Exception: for **`LOW_SAMPLE_CONDITIONS`** (`onycholysis`,
  `leukonychia`, `lindsays_nails` as of 2026-09-16 - all three have a CNN class again
  via the `nihati` dataset but only n=4-6 held-out eval positives, an order of
  magnitude below the n=18 that used to gate `splinter_hemorrhages`'s membership here;
  `splinter_hemorrhages` itself was removed from this set once chaa grew its held-out
  test count to n=50 with 0.98 isolated-crop recall, see "Dataset contamination"
  below), disagreement instead falls back to `inconclusive` (`"low_sample_disagree"`, `failure_reason:
  "insufficient_data_for_confident_call"`) rather than letting the CNN unilaterally
  overrule the heuristic - there isn't enough held-out evidence to justify asserting a
  verdict against the other signal. Agreement (both signals concur) is unaffected by
  this exception. A confident
  prediction of a *different* condition is treated as "no opinion" (single-label can't
  rule out a co-occurring sign). `ResultView.jsx` renders `color_fused` with a "Color +
  AI" badge.
  Class-weighting note: `train_color_classifier.py` uses **sqrt-dampened** inverse-
  frequency class weights, not raw inverse frequency - when melanonychia/mees_lines
  (two small classes) were first added, raw inverse-frequency weighting over-corrected
  for them and regressed the real-photo false-positive rate on leukonychia/pitting/
  pallor/onycholysis/splinter_hemorrhages (measured via `/analyze`, not just test-set
  accuracy). Sqrt-dampening plus more epochs fixed it - re-verify with a real `/analyze`
  false-positive check (not just `eval_color_ensemble.py`) after any future retrain that
  adds a new small class, since test-set accuracy alone didn't catch the regression.

Same honesty caveats as the geometry CNN: trained on KNM **clinical** photos, not phone
photos - real-world accuracy is unknown/lower and never clinical-grade; output stays
within / outside / inconclusive, never a diagnosis.

**Tuned decision tables + validation policy (2026-09-12).** The first unified
recall-*and*-false-positive run (`ml/eval/eval_end_to_end.py`, which scores every
condition on healthy images from all three sources: Ghana non-anemic, KNM healthy,
nail-disease normal) showed the shipped rules false-positived badly on healthy nails -
TEST: pitting 32.7%, leukonychia 30.3%, pallor 28.5%, cyanosis 18.2%. The older ~1%
figures did not include this healthy mix. Attribution on valid: every
pitting/cyanosis/leukonychia/splinter false positive was `color_only` - mostly
darker-skin healthy nails the CNN read as "pallor", which fusion treated as "no
opinion" on the other conditions, handing them to the near-chance heuristic.
`ml/eval/tune_color_decision.py` replays cached probabilities through the production
`color_classifier.opinion_from_probs` + `color_fusion._fuse_one` (parity check: 0
mismatches) and picks, per condition on VALID only, `color_fusion.OVR_THRESHOLD` (vote
"outside" when p(C) is high even if C isn't the top class - the white-band cluster is
often a close second) and `color_fusion.HEURISTIC_MIN_CNN_SUPPORT` (heuristic-only
"outside" needs p(C) >= support, else `heuristic_uncorroborated` inconclusive). Metrics
are strict (inconclusive positives count as misses) and new healthy abstentions may only
replace removed false alarms, so abstaining can't game the score. TEST, shipped -> tuned:
cyanosis recall 75.9->89.7% / FP 17.4->3.5%; pitting 78.1->81.2% / 31.4->1.2% (but abstains
on 34% of healthy test nails); muehrckes 37.5->75.0% / 0.6->2.3%; terrys 66.7->83.3% /
0->2.3%; beaus 63.6->77.3% / 0.6->1.2%; lindsays 29.0->41.9% / 0->2.3%.
`ml/infer/validation_policy.py` then withholds verdicts (`not_validated`, original kept
as `unvalidated_verdict` for /feedback) for conditions that miss recall >= 50% and FP <= 5%
on VALID. The numbers and the unvalidated set below are as of 2026-09-12; both changed
in the retrain described next.

**Dataset contamination found and fixed; splinter_hemorrhages newly validated
(2026-09-15).** `scripts/download_data.py` already documented one rejected Roboflow
project (`tugas-akhir-kx2jl/nail-disease`, Google-scraped + watermarked, explicitly
never re-added) - but a *different*, similarly-named project, `data/raw/nail-disease`,
had been pulled and used in training for leukonychia/onycholysis/splinter_hemorrhages/
lindsays_nails for about three months without ever getting that same scrutiny. An
audit (algorithmic, at the user's explicit request - EXIF extraction, a broadened
filename regex for Google-Images/stock-photo URL fragments, an HSV-desaturation x
Canny-edge-density corner-watermark heuristic, and pytesseract OCR, run over all 1,310
raw images) found: EXIF stripped from 100% of images (uninformative - Roboflow does
this universally); filename regex caught only the same 4 source photos (10 files)
already known; OCR found no stock-photo/watermark keyword matches at all (629/1310
images had *some* OCR text, all confirmed noise from skin-texture JPEG artifacts); the
corner heuristic flagged 20 additional candidates (score 0.24-0.31), and full-resolution
visual inspection of the top 2 confirmed real, legible stock-photo watermark fragments
(e.g. "...er.com") that neither the filename check nor OCR caught. Given this dataset
had already been rejected once for exactly this failure mode and a second, independent
audit found more of it, `data/raw/nail-disease` was dropped entirely as both a training
source (`scripts/build_color_classification_dataset.py`) and an eval source
(`ml/eval/eval_color_sensitivity.py`, `ml/eval/eval_end_to_end.py`) - not just for the
licensing reason that got `nail-dataset-arthitaya` dropped, but because its CC BY
relicense claim itself isn't trustworthy, which taints local-only eval use too, unlike
a pure licensing gap.

The `chaa/yolov8-nails-segmentation-ckvkd` Roboflow set (CC BY 4.0, YOLO **segmentation**
format - polygon labels, not fixed-length boxes; `scripts/build_color_classification_
dataset.py`'s `_row_bbox` reduces a polygon to its axis-aligned bounding box before the
existing crop step) replaced it for splinter_hemorrhages: Healthy/Splinter Hemorrhage/
Spoon Nail/Terry's-nail, ~1,947 images, re-split by image stem like the source it
replaced. leukonychia, onycholysis and lindsays_nails have no replacement source and
lost their only CNN backing and their only eval positives; onycholysis was already
CNN-uncovered-caliber (see `LOW_SAMPLE_CONDITIONS` above), but leukonychia and
especially lindsays_nails (previously borderline-*passing* the validation policy on
nail-disease-sourced eval data) are a real, if small, capability loss - the honest
trade for removing data whose provenance can't be trusted, not a free win.

Effect on the retrained ensemble (`ml/eval/eval_color_ensemble.py`, isolated CNN,
12 classes now instead of 16): overall test accuracy 0.757 (app conditions + healthy
0.772); splinter_hemorrhages recall 0.980 (n=50, up from a training pool an order of
magnitude smaller under nail-disease). End-to-end, through `/analyze`
(`ml/eval/eval_end_to_end.py` + `ml/eval/tune_color_decision.py`, chosen on VALID,
reported on TEST): splinter_hemorrhages valid 83.8%/2.4% FP -> test 71.7%/1.5% FP,
clearing the 50%/5% policy bar for the first time (previously 11.8%/1.7% test on the
nail-disease-sourced model) - it moved OUT of `UNVALIDATED_CONDITIONS`.
`color_fusion.LOW_SAMPLE_CONDITIONS` dropped splinter_hemorrhages too (test n grew from
18 to 46-48). lindsays_nails moved INTO `UNVALIDATED_CONDITIONS` (0 eval positives with
no source left). cyanosis/terrys_nails/beaus_lines/muehrckes_lines/pitting were
re-tuned against the retrained model and stayed validated, though beaus_lines and
muehrckes_lines have a real valid->test recall gap worth watching on the next retrain
(small test-split n) - see `ml/infer/validation_policy.py`'s and `ml/infer/
color_fusion.py`'s comments for the exact numbers. Full before/after and audit
methodology: `Decision Log.md` and `Change Log.md` in the Obsidian vault, dated
2026-09-15/16.

Two eval-script bugs were fixed as part of this, unrelated to the dataset change but
found while re-running these evals: `ml/eval/eval_end_to_end.py`'s real-DB-write guard
did a raw substring check of `tempfile.gettempdir()` against a forward-slash-normalized
URI, which always failed on Windows (backslash vs. forward-slash separators) - fixed by
normalizing both sides before comparing. `ml/eval/tune_color_decision.py` crashed
(`max() of empty sequence`) on any condition with zero held-out positives, a case that
didn't exist before this retrain (every app condition used to have at least a few
nail-disease-sourced positives) - fixed to skip tuning and report `n/a` for such a
condition instead.

**Two more datasets vetted and added; validated set unchanged despite the added data
(2026-09-16).** Following the `nail-disease` contamination above, two candidate
replacements suggested by independent research were each put through the same
algorithmic audit (EXIF, filename/stock-site regex, OCR, corner-watermark heuristic)
before being trusted, rather than taking a license tag at face value:
- **`nihati` (nail-disease-classification-nihati, Roboflow, CC BY 4.0)** - 2,047 images,
  folder-classification format. No exportable Roboflow "version" existed
  (`.version(1).download()` failed, `proj.versions()` returned `[]`), so it was pulled
  via the SDK's public `Project.search()`/`Project.image()` methods instead (no sign-in
  needed). The audit found EXIF stripped universally (uninformative, as with every
  Roboflow set), no stock-site filename matches, no OCR watermark-keyword hits, and the
  corner-watermark heuristic's top scores (0.30-0.41) were all confirmed, on visual
  inspection, to be textured fabric backgrounds, not watermarks - a different false-
  positive mechanism than `nail-disease`'s but correctly distinguished by looking at the
  actual images rather than trusting the score. Ingested into
  `scripts/build_color_classification_dataset.py` (`add_nihati`) re-split by image id
  (md5 bucket, same scheme as chaa) since its own split isn't a trusted signal here.
  Restores leukonychia (40/5/4 train/valid/test), lindsays_nails (27/6/5), and
  onycholysis (27/5/8) as CNN classes for the first time since `nail-disease`'s removal.
- **`anemia` (anemia-hv9cy/nails-pceph v1, Roboflow, YOLO detection)** - only the
  `anemic_nail` class (1,043 train + 41 valid + 20 test boxes) is ingested, mapped to
  `pallor`; `anemic_toung`/`non_anemic_tounge` boxes are skipped as out-of-scope. Note:
  this export's `data.yaml` is missing a `non_anemic_nail` class that its name implies
  should exist - confirmed absent by auditing every label file's class indices (only
  0/1/2 ever appear) - a transparency note, not a blocker, since only the labeled
  `anemic_nail` positives are used. Also found: ~8.5% of the dataset's *unlabeled*
  background images are Pexels/Unsplash stock photos by filename pattern - cross-checked
  that none of the actual ingested `anemic_nail` boxes come from those files, so it
  doesn't taint what's actually trained on, but it's noted here rather than silently
  ignored.

Both sources are also wired into `ml/eval/eval_color_sensitivity.py` and
`ml/eval/eval_end_to_end.py`'s eval-positive gatherers (re-split the same way as
training, filtered to the eval split, so no leakage). Net effect on the retrained
15-class ensemble (`ml/eval/eval_color_ensemble.py`): test accuracy 0.745–0.756
(mobilenet/efficientnet solo numbers), leukonychia/onycholysis/lindsays_nails now have
real (if small, n=4-8) isolated-CNN precision/recall instead of not existing as classes.
**End-to-end, the validated set did not change**: `leukonychia` and `lindsays_nails`
initially looked like they cleared `validation_policy.py`'s 50%/5% bar on VALID (recall
80%/83%), but that number relied on letting the CNN's `ml_primary` override the
heuristic on disagreement with only n=5/6 held-out positives backing it - adding both
(and `onycholysis`) to `color_fusion.LOW_SAMPLE_CONDITIONS` (matching the precedent that
gated `splinter_hemorrhages` there until its test-n reached 50) dropped their honest
strict recall to 40%/0%/0%. All three stay in `validation_policy.UNVALIDATED_CONDITIONS`
- NIHATI meaningfully improved isolated-CNN accuracy and gave the app real CNN coverage
for these conditions again, but not enough held-out evidence yet to trust an end-to-end
verdict. `terrys_nails` did move: a lower floor (0.25, was the 0.45 default) and OVR
(0.3, was 0.4) picked by `ml/eval/tune_color_decision.py` against the larger eval pool
raised its valid recall 44.1%->50.0% (test 44.7%), keeping it just inside the policy
bar. Full numbers: `ml/infer/color_fusion.py`'s and `ml/infer/validation_policy.py`'s
table/docstring comments; audit methodology and before/after in the Obsidian vault's
`Change Log.md`/`Decision Log.md`, dated 2026-09-16.

**CNN-only conditions: onychogryphosis added as a 14th condition (2026-09-23).** The color
CNN already trained on KNM's `onychogryphosis` class (purely as a discriminator), so it
was promoted to a reported condition with no retrain: appended to the manifest's
`app_conditions` and to `train_color_classifier.APP_CONDITIONS`, and added to
`eval_color_sensitivity.KNM_SLUGS` so the end-to-end eval has positives. Thickening and
curvature aren't a color/texture pattern, so there is no classical heuristic:
`ml/infer/onychogryphosis.py` only supplies the finding shape, and its `build_finding`
returns `inconclusive` (`requires_ai_model`), **never** a default `within`, so a torch-free
install says "couldn't analyze" instead of pretending to rule it out.
`color_fusion.CNN_ONLY_CONDITIONS` short-circuits `_fuse_one` before the heuristic path:
a confident CNN call sets the verdict (`agreement: "ml_only"`), otherwise it is
`inconclusive` (`no_confident_ai_call`). Tuned `OVR_THRESHOLD["onychogryphosis"] = 0.15`
on VALID: strict valid 72.3% recall / 0.0% FP -> test 67.6% / 0.0% FP (n_pos 65/34), so it
is validated. Its real cost is abstention: roughly a third of healthy nails get
`no_confident_ai_call` for it, because the CNN is often confidently calling a
*different* class (for example Ghana healthy->pallor), which is "no opinion" for this one.
Every other condition's numbers were unchanged by the addition. Unlike the other signs,
it's usually a local nail problem (pressure, injury, aging, fungal infection, poor
circulation), not a systemic one, and the UI copy says so. Adding another CNN-only
condition: same four steps (module, `_COLOR_CONDITIONS`, `app_conditions`,
`CNN_ONLY_CONDITIONS`), plus i18n in all six locales.

**Per-sign specialists (2026-10-17): onycholysis and leukonychia.** Their heuristics are near-chance and the shared color CNN stays under the low-sample guard, so each has a dedicated EfficientNet-B0 (2 seeds, 8-way TTA) served by `ml/infer/specialists.py` (`ENABLED` allowlist; weights + cutoff in `ml/models/<sign>_specialist.{pt,json}`, gitignored). Regenerate: `scripts/build_onycholysis_app_crops.py` (caches the production front end's crops of every source photo into `data/raw/onych_app_crops`), then `scripts/train_onycholysis_specialist.py --target <sign> --ind-root data/raw/onych_app_crops [--tag app_ | --final]` (`--tag app_` = leave-one-source-out folds, `--final` = ship model). Trained on the app's OWN crops (nail_locator + `compute_nail_region`) plus the Han clinical set (`data/raw/han_canon`, tip-down). `pipeline.analyze_top_color` calls `specialists.apply`, which swaps a specialist's call in for that sign's finding (`track_used: "color_fused"`, `agreement: "ml_only"`) and passes through when torch/weights are absent. **Lesson:** an onycholysis model trained and scored on clean pre-cropped nails (92.9% recall / 5.4% FP) fell to 81.0% / 15.7% through the real front end; training on app-style crops fixed it. Cutoffs were picked after seeing score curves (mildly optimistic): onycholysis 0.3 - final model 96% recall / 1.3% FP (n=25 / 237), leave-one-source-out pooled 78.9% recall (n=95) / 4.2% FP (n=551), thin margin; leukonychia 0.2 - final valid+test 90.5% / 0.8% (n=21 / 237), pooled LOSO 86.3% (n=102) / 3.6% (n=551), NIHATI held out alone 69.0% / 3.6%. Both left `UNVALIDATED_CONDITIONS`. Arthitaya's own healthy photos fire 12-43% at low cutoffs when it is held out. Tight source photos, never phone photos; Han has not had the watermark audit. **melanonychia (enabled later the same day, cutoff 0.005):** trained on Han positives only (Arthitaya is eval-only, never trained on) with Ghana darker-skin healthy patches + KNM/chaa/NIHATI healthy as negatives (`--extra-real ghana`, 4 seeds). The first no-Ghana version was withheld (5.3% FP on Ghana healthy). Final: Arthitaya positives n=58 vs 593 healthy: recall 69.0% / FP 0.7% at the cutoff (81.0% / 2.5% at 0.002); through the real `/analyze` on all 60 Arthitaya positives: 66.7% strict recall (40/60, 2 abstained), 1/40 healthy false alarm. Caveats: one positive source, recall on darker-skin melanonychia unmeasured, Ghana healthy are small masked patches, cutoff picked post-hoc, scores are tiny so the cutoff is on a very low scale (rank-order, not a probability). **Terry's specialist was tried and rejected** (leave-one-source-out pooled recall at 5% FP about 51%).

**Koilonychia via the top-photo appearance route (2026-10-17).** `ml/infer/appearance.py` already answered clubbing/koilonychia from the color CNN's read of the top photo whenever side geometry is unusable (which the measurement gate makes the norm on phone photos), but the manifest never listed any sign, so it was off. `scripts/enable_appearance_route.py` writes `appearance_conditions/appearance_rules/validated_appearance_conditions/validated_roi_modes` into `ml/models/nail_color_classifier_labels.json` (gitignored; re-run it after retraining the color CNN) for **koilonychia only**, rule floor 0.1 picked on VALID by `tune_color_decision.py` (`eval_end_to_end.py --include-shapes --include-authorized`): valid 78.0% recall / 2.2% healthy FP (n=109 / 318), test 70.8% / 3.8% (n=72 / 240); test by source KNM 79%, chaa 64%, NIHATI 2/2; healthy false alarms chaa 11% (6/54), other sources ~3%. Real `/analyze` on TEST with a blank side photo: 51/72 positives "outside" (strict, 20 abstained as `camera_feed_blank`); the one real healthy phone subject reads "within" for koilonychia in all 9 hand crops. **Clubbing does not clear the bar through this route** (valid 43.8%, test 50.0%) and stays off. Caveats: the sign is defined by nail curvature, which a top-down photo only hints at; these are source-dataset photos; the FP margin under 5% is thin.

**Real-photo check found a melanonychia false alarm (2026-10-17).** The single real healthy phone subject (`data/real_eval/healthy/anish1_*`, darker skin, a dark band at the distal edge of the nail) reads melanonychia "outside" in all 9 hand-made nail crops, while onycholysis, leukonychia and koilonychia all read "within". One subject cannot size the problem, but it is the only phone evidence and it is negative; treat melanonychia as unconfirmed on phones. To hold it back: remove it from `specialists.ENABLED` and add it back to `validation_policy.UNVALIDATED_CONDITIONS`.

**False-positive reduction (2026-10-18).** `ml/eval/scan_healthy_fp.py` pushes 558 healthy dataset photos (valid+test, all sources) through `/analyze` and counts what the user would see: each condition was under 5% alone, but 13.8% of healthy nails (77/558) got at least one "outside" flag. Made the app less sensitive: leukonychia and onycholysis specialist cutoffs 0.2/0.3 -> 0.5 (leukonychia recall 90.5% -> 81.0%, healthy FP 1.5% -> 0.2%; onycholysis 96% / 0.4%); `color_fusion` cyanosis ovr 0.15 + support 0.1 (valid 56.9%/2.5% -> 53.8%/0.6%), splinter ovr 0.4 (71.4%/2.8% -> 65.3%/1.6%); koilonychia appearance floor 0.1 -> 0.3 (valid 78.0%/2.2% -> 58.7%/1.3%, test 70.8%/3.8% -> 63.9%/1.7%; `scripts/enable_appearance_route.py` updated, re-run it after any manifest regeneration). **Withheld (added to `UNVALIDATED_CONDITIONS`, removed from `specialists.ENABLED`):** melanonychia (the real healthy phone subject scores 0.05-0.16 on its specialist, dataset healthy < 0.005, so no cutoff clears the phone photo without dropping dataset recall to ~33%) and terrys_nails (largest source of false alarms, VALID recall 48.7% under any tighter rule, labels mostly not visually Terry's). Result of the same scan: 6.3% of healthy nails (35/558) get any flag (Ghana 1%, KNM 4%, NIHATI 6%, chaa 26%, Arthitaya 2/16); chaa-sourced healthy nails still drive most of it (koilonychia, splinter, cyanosis, pitting). Cost: recall on the tightened conditions is lower than the numbers quoted above for them; those older numbers describe the previous, more sensitive settings. Reverting any of these is one constant each.

**Independent photo-set check (2026-10-18).** The Hb skin+fingernail set (Yakimov et al. 2024, Figshare, CC0 record, `E:\NailIQ_data\raw\hb_skin_nails_figshare`, 250 patients x 3 labelled nails; boxes are `[y0, x0, y1, x1]`) is used for EVALUATION ONLY via `ml/eval/scan_hb_nails.py` (no disease labels, so flags are an upper bound on false alarms). The 800x600 photos have ~50px nails, so the app's quality gates abstain on most: only 45 of 750 nails were readable in detector mode and none in `--assisted` mode (dataset nail box passed). Among the 45 readable: muehrckes_lines flagged 22 (49%, ordinary-looking nails, vs 0.4% on the dataset scan) -> withheld (`UNVALIDATED_CONDITIONS`); koilonychia 5 of 7 readable (too few to size); every other condition 0-1 flags. A first run used the wrong box order and fed the app empty background, which gave leukonychia "outside" on a nail-free crop (a robustness gap, not fixed). The dataset healthy numbers above do not transfer to real-camera photos; treat them as optimistic.

**Healthy-signal gate and no-finger guard (2026-10-18).** `color_fusion.HEALTHY_MAX` (splinter_hemorrhages, pitting: 0.1) withholds a specific "outside" (inconclusive, `agreement: "healthy_signal"`) when the color CNN still gives `healthy` >= 0.1 - the idea (networks separate healthy from diseased better than they name the disease) comes from Oehler's Han-replication README; no code or weights from that unlicensed repo were used. Tuned on cached VALID probabilities, TEST confirmed; compounded with the earlier tightening, strict now: splinter valid 53.1%/0.9%, test 64.2%/0.4%; pitting valid 60.7%/0.0%, test 68.8%/0.4%; cyanosis was tried and rejected (valid recall 57% -> 42%). `nail_region.compute_nail_region` now refuses (`nail_region_unclear`) when no nail box is given and the finger mask is a neutral backdrop blob (median Lab chroma < 3.5): a white-table blob had produced leukonychia "outside". It also abstains on grayscale photos. Healthy scan after both: 22/558 (3.9%) get any visible flag (was 13.8% before today's work, 6.3% mid-way), but every-condition abstention rose from 15 to 43 healthy nails (7.7%). Not measured separately: the guard's own effect on dataset positives (confounded with the earlier tightening in the comparison caches).

### Eval / diagnostics (`ml/eval/`)

- `grad_cam.py` - Grad-CAM overlays (last conv block) on test images, written to
  `ml/eval/gradcam_out/` (gitignored), to confirm the model attends to the nail,
  not the background. Good judging/demo artifact.
- `eval_real.py` - runs the **full inference path** (ROI + TTA + temperature) over
  real phone photos in `data/real_eval/<label>/` (gitignored, personal images) and
  reports a confusion matrix + per-class recall. This is the number that matters;
  the training split accuracy doesn't reflect phone photos.
- `eval_real_color.py` - the color track's sibling to `eval_real.py`: runs real phone
  photos in `data/real_eval_color/<condition-or-healthy>/` (gitignored) through the
  full `/analyze` path. **As of this writing it has never been run against real
  data** - no camera/subject was available to generate labeled phone photos
  autonomously, so this is a harness waiting on real photos, not a result. Every
  color-track number elsewhere in this doc (`eval_color_ensemble.py`,
  `eval_color_sensitivity.py`) is measured on clinical/dataset images; real
  phone-photo accuracy for the color track remains genuinely unmeasured. Even
  10-20 labeled photos per condition would make this meaningful.
- `eval_color_sensitivity.py` - **the color track's most important number, and the
  one most likely to surprise you.** `eval_color_ensemble.py` measures the CNN in
  isolation on pre-cropped nail-plate images; this script instead runs known-positive
  **full, uncropped** images (from the same held-out test split, re-derived via the
  build script's exact `bucket_split`/KNM-native-split logic so there's no leakage)
  through the real Flask `/analyze` endpoint - region detection, bbox crop, and
  `color_fusion` included - with the same realistic-framing simulation used for
  false-positive checks. Recall here is consistently **worse** than the CNN-only
  numbers because the CNN's per-class confidence floors (tuned against clean crops)
  throw away true positives once bbox-crop noise is folded back in, falling back to
  the classical heuristic, which is also weak. First run: pitting 82.8% and
  leukonychia 76.0% hold up well, but pallor 28.0%, onycholysis 19.0%, and
  splinter_hemorrhages 14.3% miss most real cases end-to-end despite reasonable
  CNN-only numbers - this is the gap that matters for a screener and the CNN-only
  eval alone will not surface it. Re-run after any retrain or threshold change.
  Pallor's gap was a threshold problem and got fixed (see `CLASS_CONFIDENCE_THRESHOLD`
  below); onycholysis/splinter_hemorrhages/lindsays_nails were diagnosed further (per
  finding, real `f["ml"]` prediction inspected) and are NOT a threshold problem: the
  classical heuristic is essentially blind on these three (`heuristic=within` on
  nearly every miss, matching its documented near-chance calibration), and when the
  CNN abstains it's usually genuinely unsure (confidence 0.2-0.4) - but a meaningful
  share of the misses are the CNN **confidently wrong about a neighboring class**
  (onycholysis mistaken for lindsays_nails at conf 0.63, leukonychia at 0.59,
  muehrckes_lines at 0.87; lindsays_nails mistaken for beaus_lines at 0.91,
  leukonychia at 0.999). These five conditions (leukonychia, lindsays_nails,
  muehrckes_lines, beaus_lines, onycholysis) all present as some form of pale/white
  discoloration or banding, and the CNN confuses between them under real (noisier)
  bbox crops more than the clean-crop test-set numbers suggest. No confidence-floor
  change can fix a confident vote for the wrong class in this cluster - that's inter-
  class discrimination capacity, not calibration. A hierarchical classifier (first
  "which of this white-patch cluster," then discriminate within it) or higher-res
  crops are the plausible fixes, but both are bigger changes than a threshold tweak
  and weren't attempted this session.
  **Post-arthitaya-removal update:** dropping the unlicensed arthitaya source (see
  "The color-condition CNN track" above) cost real recall beyond the numbers above,
  since arthitaya had also contributed some onycholysis training images -
  onycholysis end-to-end recall fell further, to 0% (0/19) in the retrain that
  removed it, and splinter_hemorrhages fell from 28.6% to 18.2%; their false-positive
  rates stayed flat or improved slightly (onycholysis 3.5%->2.9%, splinter_hemorrhages
  7.9%->12.4%, mixed). This is the real, measured cost of closing the license gap, not
  a hypothetical one - onycholysis in particular is now close to never firing a
  correct positive end-to-end. `color_fusion.py`'s new `LOW_SAMPLE_CONDITIONS`
  disagreement-to-inconclusive path (see "Fusing the two tracks" section) accounts
  for part of this: some cases that used to resolve (rightly or wrongly) to a verdict
  now honestly resolve to `insufficient_data_for_confident_call` instead. Both
  conditions need materially more/better data to become useful screeners; no
  threshold or fusion change can substitute for that.

**`healthy` recall is weak (0.451 ensemble) but it's a single-cohort problem, not a
general model weakness - confirmed, not just theorized:** a raw-argmax confusion
check found 72% of all `healthy` misclassifications go to `pallor` (73/101), and a
follow-up split by image source nailed down exactly why: on the `healthy` test
split, **100% of the healthy->pallor errors (73/73) are Ghana-cohort images; 0/58
non-Ghana healthy images (KNM/NailCheck/merged) are ever confused with pallor.**
Checked again on the *train* split for a hard-negative-mining attempt: 383/384
healthy images the model calls "pallor" are Ghana; only 1/819 non-Ghana healthy
images is. This means the CNN's real-world healthy/disease separation is fine - the
weak aggregate number is entirely the Ghana anemic-vs-non-anemic distinction being
genuinely hard (the classical heuristic documented this as near-chance before the
CNN was ever added), concentrated in one sub-population of one class. Oversampling
the confused Ghana images in training was considered and **not attempted**: the
train-set confusion rate (27.7% of Ghana healthy images) shows the model already
sees these images constantly and still can't separate them, so more repetition of
the same images is unlikely to add information the pixels don't already carry -
this reads as a genuine visual/data ceiling, not a fixable training artifact.
This is NOT a user-facing problem regardless: `predict_from_region`'s per-class
floor (`pallor` needs 0.45, see `CLASS_CONFIDENCE_THRESHOLD`) filters almost all of
these low-confidence healthy->pallor guesses into "no opinion" before
`color_fusion` sees them, which is why the real end-to-end pallor false-positive
rate is only ~1% (see `fp_rate`-style checks) despite this raw confusion. The floor
is doing the real work here, not the CNN's discrimination - don't lower `pallor`'s
threshold without re-checking both this confusion rate and the false-positive rate.

**A second fix angle was tried and also failed - probability-margin gating.** Theory:
maybe healthy-misclassified-as-pallor cases are lower-confidence/closer-call than true
pallor cases, so gating on `probs["pallor"] - probs["healthy"]` (a signal
`predict_from_region` computes but doesn't currently use) could separate them without
new data. Measured directly on the color-CNN test split's healthy+pallor images: at
margin >= 0.30 (a stringent gate), precision only moves 0.715 -> 0.754 while recall
drops from 0.904 to 0.774 - the two classes' margin distributions overlap almost
completely (true pallor cases have plenty of low-margin examples too). Not worth
shipping for that trade. This confirms the earlier conclusion from a different angle:
the healthy/pallor confusion is a genuine information ceiling in this cohort's pixels,
not a decision-rule problem - a smarter threshold or margin gate doesn't recover it,
only more/different training data would.

**Trap for any script that drives `/analyze` in a loop:** `backend/app.py` rate-limits
`/analyze`/`/validate_photo`/`/feedback` to 30 req/60s per IP, and the Flask test client
looks like one IP making dozens of rapid requests. Early testing this session mistook
the resulting HTTP 429s for real pipeline rejections - the false-positive/sensitivity
scripts above all monkeypatch `app_module._rate_limited = lambda ip: False` before
building the test client for exactly this reason. Forgetting it silently caps any
batch eval at ~30 analyzed images and inflates the apparent rejection rate.

### Frontend component contract

- `CameraCapture.jsx` owns the two-step capture flow internally and only calls
  `onCapture({ sideImage, topImage })` once both shots are taken - `App.jsx` never
  needs to know about the two-step mechanics.
- `ResultView.jsx` renders one finding-card per item in `result.findings`, mapping
  `verdict` through a `COPY` lookup (`within` / `outside` / `inconclusive`) for
  icon/label/message. Any new finding type automatically gets card rendering for
  free as long as it follows the same `{label, display_name, value, unit, verdict,
  confidence, failure_reason}` shape. `track_used: "fused"` findings show a
  "Geometry + AI" badge plus an agreement note (from `agreement`) and the model's
  closest visual match (from `ml.predicted_label`); `track_used: "color"` findings
  show a "Color check" badge; the legacy `track_used: "ml"` badge path is still
  handled for standalone ML findings.
- `api.js` is the only place that knows the `/analyze` request/response shape
  (`VITE_API_BASE` env var overrides the default `http://localhost:5000`).
- **i18n + accessibility (`frontend/src/i18n/`)**: every user-facing string lives
  in the locale dictionaries (`en.js` is the master/fallback, `es.js` mirrors it)  -
  don't hardcode UI copy in components; use `useI18n()`'s `t('dot.path', {params})`.
  Adding a language = one new dictionary file registered in `i18n/index.jsx`.
  Condition copy lives under `conditions.<key>` in the dictionaries;
  `conditions.js` only holds structure (keys/icons) and localized getters.
  Backend findings arrive with English `display_name`; the UI renames by `label`
  via `findingName()` (`findingNames` in the dictionaries) so the API contract is
  untouched - backend-generated strings like `tone_caveat` are the one thing that
  stays English in other languages. `SettingsProvider` (wraps App in `main.jsx`)
  also persists high-contrast / large-text / reduce-motion prefs to localStorage
  and reflects them as `a11y-*` classes on `<html>`; App.css font sizes are rem
  on purpose so the large-text root font-size bump scales type - don't add new
  `font-size: ...px` rules.

### Scan history

`/analyze` persists every scan: `backend/models.py`'s `ScanRecord` (SQLite via
flask-sqlalchemy, `findings_json` + `created_at`) is written after analysis runs
(`backend/app.py`'s `/analyze`), and the response includes `scan_id`. A DB write
failure is swallowed (rolled back) rather than failing the request - history
logging must never block a result. `GET /history` returns all `ScanRecord`s
newest-first. `Feedback` (also in `models.py`) records a user's "does this match
what you see?" response per finding (`scan_id` FK, `label`, `shown_verdict`,
`agreed`, optional `note`) via `POST /feedback` - the honest data path toward
calibrating the uncalibrated color/geometry thresholds later. Neither model
stores images, only findings/labels.

`frontend/src/components/HistoryView.jsx` calls `getHistory()` (`api.js`) and
renders each scan as a card (per-finding verdict rows, an overall status, a
"Changed" badge when a finding's verdict flipped vs. the previous scan) plus an
`AngleTrend` Recharts line chart tracking the `clubbing` finding's `value` across
scans (renders only once ≥2 scans have that finding). No image is ever shown in
history, only findings.

### Data pipeline

`scripts/download_data.py` pulls nail-image datasets (Roboflow Universe, CC BY 4.0)
into `data/raw/` - needs a free `ROBOFLOW_API_KEY`. `data/raw/nailcheck-3xvkl` is
the classification set the CNN trains on (Clubbing/Koilonychia/Healthy + 5 more
classes, already train/valid/test split). `data/raw/LICENSES.md` (generated) tracks
attribution - CC BY 4.0 requires crediting each source in any submission/README.
`data/raw/` is gitignored (don't commit the images/licensing); re-run the script to
repopulate. The other detection datasets (`nail-clubbing`, etc.) are boxes, not
class folders - not yet wired into training (would need a crop step). `ROBOFLOW_API_KEY`
can also live in `backend/.env` (the script loads it via `python-dotenv` if the plain
env var isn't set) - the same file `DEEPL_API_KEY` already lives in.

`data/raw/nail-disease` was a training/eval source until 2026-09-15, when it was removed
for confirmed watermark contamination - see "Dataset contamination found and fixed" under
the color-condition CNN track above. It is deliberately absent from `download_data.py`'s
`DATASETS` list; don't re-add it without re-running that audit.

`scripts/build_provenance_manifest.py` generates `data/raw/color_cls_provenance.csv`
(gitignored, one row per training image: path, split, class label, source dataset,
license, and what's actually known about how that source established its label) - run
it after `build_color_classification_dataset.py`. `ATTRIBUTION.md`/`data/raw/LICENSES.md`
record provenance per DATASET; this is the per-IMAGE counterpart, added 2026-09-18 because
tracking provenance only at the dataset level was exactly what let `data/raw/nail-disease`'s
contamination go unnoticed for months - a per-image record makes "which images came from
which source" a lookup, not a re-investigation, the next time a source's trustworthiness is
questioned.

`data/raw/nail-disease-classification-nihati` and `data/raw/anemia-nails-detection` were
added 2026-09-16 as vetted replacements/backfill - see "Two more datasets vetted and
added" under the color-condition CNN track above for the audit methodology and why the
validated set didn't change despite the new data. NIHATI has no exportable Roboflow
version, so it isn't in `download_data.py`'s normal `DATASETS`/`.download()` flow; it was
pulled via the Roboflow SDK's `Project.search()`/`Project.image()` public API instead
(one-off, not yet folded into `download_data.py` as a repeatable step - re-downloading it
would need the same approach). `anemia-nails-detection` is a normal YOLO-detection
Roboflow export and could be added to `DATASETS` if it needs to be repeatable.


## Canonical Obsidian vault — required project memory workflow

User instruction (2026-09-05): the app history and future work belong in `C:\Users\Anish\OneDrive - Lake Washington School District\Desktop\Obsidian Vaults\NailIQ`. Before working, read `Home.md`, `Current State.md`, `Next Actions.md` and relevant historical notes there. Reference this vault first for prior decisions/events. After every meaningful code, research, design, evaluation, dataset/model, outreach or planning change, update the affected notes and append a dated `Change Log.md` entry with evidence, verification and remaining work. Preserve superseded decisions and distinguish proposals from completed actions. Run `backend/venv/Scripts/python.exe scripts/sync_obsidian_vault.py` from the repo root to refresh generated source/history evidence; it does not replace authored notes. Never claim missing history, outreach or unrun tests as completed. Follow `Vault Maintenance.md`.
