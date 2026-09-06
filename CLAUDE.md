# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NailIQ: a precautionary screener for nail-based signs of systemic disease. It
covers thirteen conditions across four tracks: digital clubbing and koilonychia/spoon
nails (side-profile geometry, fused with a top-down CNN), and eleven top-down
color/texture signs - leukonychia, melanonychia, pallor, cyanosis, Terry's nails,
Lindsay's nails, onycholysis, Beau's lines, Muehrcke's lines, splinter hemorrhages,
and pitting - five of which (cyanosis, Terry's nails, Beau's lines, Muehrcke's
lines, pitting) are further fused with a second color-condition CNN ensemble.
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
backend/venv/Scripts/python.exe ml/train/train_color_classifier.py --backbone mobilenet_v3_large  # color-condition CNN
backend/venv/Scripts/python.exe ml/train/train_color_classifier.py --backbone efficientnet_b0     # adds to color ensemble
backend/venv/Scripts/python.exe ml/eval/eval_color_ensemble.py  # color ensemble accuracy (what ships)
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
  (from KNM), pallor (Ghana fingernail-anemia set, see `data/DATASETS_DIVERSITY.md`),
  leukonychia/onycholysis/splinter_hemorrhages/lindsays_nails (from the
  `nail-disease` Roboflow set, added because as pure heuristics they false-positived
  badly on healthy nails). **melanonychia is deliberately NOT in this list** - it was
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
  `splinter_hemorrhages` - test-set n of 24 and 18, where a single example flips
  precision/recall by 5-15 points), disagreement instead falls back to `inconclusive`
  (`"low_sample_disagree"`, `failure_reason: "insufficient_data_for_confident_call"`)
  rather than letting the CNN unilaterally overrule the heuristic - neither signal has
  enough held-out evidence to justify asserting a verdict against the other for these
  two. Agreement (both signals concur) is unaffected by this exception. A confident
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
class folders - not yet wired into training (would need a crop step).


## Canonical Obsidian vault — required project memory workflow

User instruction (2026-09-05): the app history and future work belong in `C:\Users\Anish\OneDrive - Lake Washington School District\Desktop\Obsidian Vaults\NailIQ`. Before working, read `Home.md`, `Current State.md`, `Next Actions.md` and relevant historical notes there. Reference this vault first for prior decisions/events. After every meaningful code, research, design, evaluation, dataset/model, outreach or planning change, update the affected notes and append a dated `Change Log.md` entry with evidence, verification and remaining work. Preserve superseded decisions and distinguish proposals from completed actions. Run `backend/venv/Scripts/python.exe scripts/sync_obsidian_vault.py` from the repo root to refresh generated source/history evidence; it does not replace authored notes. Never claim missing history, outreach or unrun tests as completed. Follow `Vault Maintenance.md`.
