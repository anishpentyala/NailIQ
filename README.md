# NailIQ

A precautionary screener for nail-based signs of systemic disease. Digital clubbing
is present in ~35% of non-small-cell lung cancer cases and is also linked to heart
disease, COPD, and liver disease; koilonychia (spoon nails) is linked to iron
deficiency anemia. Both develop slowly and are rarely self-noticed. NailIQ lets
anyone photograph their finger and get a quick, honest read on whether their nail
signs are worth mentioning to a doctor.

**This is not a diagnostic tool.** It never names a disease or says "you have
clubbing." Each finding is only ever "within typical range," "outside typical
range," or "couldn't analyze this photo" — and always recommends following up with a
doctor. Every screen carries this framing.

## How it analyzes a photo

Each scan captures a **side-profile** and a **top-down** photo, and runs two
independent computer-vision tracks that are **fused into one verdict per condition**:

| Track | What it does | Owns |
|-------|--------------|------|
| **Geometry** (`ml/infer/`) | Classical OpenCV — Lovibond nail angle (cosine rule) + koilonychia sagitta from the finger contour. No trained model needed. | the **side profile** |
| **Trained CNN** (`ml/infer/classifier.py`) | MobileNetV3-Large classifies the nail as clubbing / koilonychia / healthy (transfer learning). | the **top-down** photo |

**Fusion** (`ml/infer/fusion.py`): when both tracks agree, confidence is boosted;
when they disagree, the result is **inconclusive** rather than a guessed verdict.
The CNN track is **optional** — torch and the weights load lazily, so the geometry
track still works in a torch-free environment.

What makes the CNN trustworthy instead of a raw softmax guess:

- **ROI crop** — the finger is cropped out of the frame *before* classifying, so the
  model keys on the nail, not the background (the biggest real-world fix).
- **Test-time augmentation** — predictions averaged over the image + its flip.
- **Temperature scaling** — logits calibrated on the validation set, so the
  confidence floor that gates "couldn't analyze" actually means something.

Grad-CAM (`ml/eval/grad_cam.py`) confirms the model attends to the nail, not the
background.

## Results

Trained on the **NailCheck** dataset (Roboflow Universe, CC BY 4.0), restricted to
clubbing / koilonychia / healthy. Last backbone blocks fine-tuned; class-weighted,
label-smoothed, phone-realistic augmentation.

**Held-out test split** (108 images) — *clean dataset images, not phone photos:*

| Class | Precision | Recall | n |
|-------|:---------:|:------:|:-:|
| clubbing | 0.94 | 0.85 | 34 |
| koilonychia | 0.83 | 1.00 | 38 |
| healthy | 0.97 | 0.83 | 36 |

**Overall accuracy 0.90.** Errors lean toward *over-flagging* conditions — the safe
direction for a screener (a false "show a doctor" beats a missed sign).

> ⚠️ This is dataset-split accuracy, **not** real-world phone-photo accuracy. Run
> `ml/eval/eval_real.py` over labeled phone shots in `data/real_eval/<class>/` to
> measure the latter. *(pending photo collection)*

## Repo layout

```
frontend/   Vite + React. Mobile-first, two-step camera capture UI.
backend/    Flask REST API. Single /analyze endpoint (base64 in, JSON out).
ml/         Training scripts + inference modules for the CV models.
  train/    CNN training (train_classifier.py: transfer learning + calibration).
  infer/    Geometry pipeline (preprocessing, keypoints, per-condition
            measurement), the trained-CNN classifier, and track fusion.
  eval/     Diagnostics: grad_cam.py (attention check), eval_real.py (phone-photo
            evaluation). Outputs gitignored.
  models/   Saved CNN weights + labels/calibration JSON (gitignored — regenerate
            by re-running training).
data/       Dataset pipeline: positive/negative examples, augmentation.
  positive/    Clubbed-finger images (sourced + licensed).
  negative/    Normal-finger images (self/volunteer captured).
  augmented/   Output of scripts/augment.py.
  raw/         Unsorted intake before triage.
scripts/    Data collection / augmentation scripts.
```

## Running it

### Backend (Flask)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5000`. `/analyze` runs real classical CV (OpenCV contour
analysis, no trained model) on the side-profile photo.

To run the geometry unit tests (synthetic point sets, no camera/dataset needed):
```bash
cd backend && venv\Scripts\activate
pytest ../ml/infer/tests/
```

### Frontend (Vite + React)

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` (Vite default). Walks through a two-step capture
(side-profile, then top-down), POSTs both to the backend, and renders one
finding-card per condition.

**Camera permissions**: most browsers require HTTPS or `localhost` for
`getUserMedia`. `localhost` is fine for local dev; testing on a phone over LAN will
need a tunnel (e.g. `ngrok`) or a dev cert.

## Retraining / evaluating the model

```bash
# from the repo root, using the backend venv:
backend/venv/Scripts/python.exe scripts/download_data.py      # needs ROBOFLOW_API_KEY
backend/venv/Scripts/python.exe ml/train/train_classifier.py  # -> ml/models/*.pt + labels json
backend/venv/Scripts/python.exe ml/eval/grad_cam.py           # -> ml/eval/gradcam_out/
backend/venv/Scripts/python.exe ml/eval/eval_real.py          # real-photo confusion matrix
```
Datasets, weights, and eval outputs are gitignored. CC BY 4.0 requires crediting
each dataset source — attribution is tracked in the generated `data/raw/LICENSES.md`.

## API contract

`POST /analyze`

Request:
```json
{
  "side_image": "<base64-encoded JPEG/PNG, no data: prefix needed>",
  "top_image": "<base64-encoded JPEG/PNG>"
}
```
`side_image` drives the geometry track; `top_image` is classified by the CNN. The
two are fused into one finding per condition.

Response (when the CNN track is available — findings are `track_used: "fused"`):
```json
{
  "findings": [
    {
      "label": "clubbing",
      "display_name": "Nail angle (clubbing)",
      "value": 165.3,
      "unit": "deg",
      "verdict": "within" | "outside" | "inconclusive",
      "confidence": 0.7,
      "track_used": "fused",
      "agreement": "agree" | "geometry_only" | "disagree" | "geometry_unavailable",
      "geometry": { "verdict": "within", "value": 165.3, "confidence": 0.7 },
      "ml": { "verdict": "within", "predicted_label": "healthy", "confidence": 0.9 },
      "failure_reason": null
    }
  ]
}
```
Without torch/weights, findings fall back to plain geometry (`track_used:
"geometric"`, no `agreement`/`geometry`/`ml` fields).

`inconclusive` means a track couldn't produce a confident verdict — the geometry
pipeline couldn't locate the finger/keypoints (`failure_reason` names the failed
check), or the two tracks disagreed (`failure_reason: "tracks_disagree"`). It never
guesses a verdict it isn't confident in. Geometry `confidence` is a heuristic from
keypoint-detection quality; ML confidence is a temperature-calibrated probability.

`POST /validate_photo`

Request: `{ "image": "<base64>", "view": "side" | "top" }`
Response: `{ "ok": true|false, "failure_reason": null | "<reason>" }`

Called right after each capture, before advancing to the next step or submitting
to `/analyze` — so a photo with no detectable finger/nail gets a retake prompt
immediately instead of after both photos are taken and the full analysis runs.

## Decisions made without asking (per project brief: "ask me nothing you can
reasonably decide yourself")

- **Vite over CRA** for the frontend — CRA is unmaintained; Vite is the current
  standard for new React apps and gives instant HMR, which matters for iterating on
  camera UI on a phone.
- **react-webcam** for camera capture rather than hand-rolled `getUserMedia` — handles
  cross-browser quirks (notably iOS Safari) so I don't have to.
- **axios** over raw `fetch` — slightly cleaner error handling for the base64 POST.
- **Recharts** (specified in brief) for the angle-history chart in step 5.
- **Flask app as a single file (`app.py`) for now** — will split into a proper package
  (`blueprints/`, `models.py`) once the SQLite history endpoint (step 5) and the real
  CV tracks (steps 3–4) land; premature structure now would just be empty scaffolding.
- **CORS wide open in dev** (`CORS(app)` with no origin restriction) since this never
  leaves localhost during development. Will lock to the deployed frontend origin
  before any real deployment.
- **`.gitignore` excludes `data/positive`, `data/negative`, `data/augmented`, `data/raw`**
  contents (kept via `.gitkeep`) — clinical/volunteer photos shouldn't live in git
  history, licensing on the clinical images is per-image and needs to stay out of a
  public repo regardless.
- **Dropped MediaPipe Hands for the geometric pipeline**, using pure OpenCV contour
  analysis instead. MediaPipe targets whole-hand poses (multiple fingers, shallow
  rotation); this app's photo is a tight single-finger close-up, a framing it
  wasn't trained for. Contour analysis is more robust for this exact composition
  and needs no external model.
- **Added a third verdict, `inconclusive`**, alongside within/outside — not a
  loosening of the "never diagnostic" rule (it still never names a condition), but
  a safety improvement: guessing within/outside when the geometry pipeline
  couldn't reliably find keypoints would be worse than asking for a retake.
- **Clubbing and koilonychia share one contour-extraction pipeline** (`ml/infer/`)
  since both are derived from the same fingertip/cuticle keypoints on the
  side-profile photo. A third geometric finding can reuse `preprocessing.py` and
  `keypoints.py` without changes.
- **Koilonychia's threshold is a rough starting estimate** — there's no labeled
  dataset yet to calibrate against. Same caveat applies to `confidence`: it's a
  heuristic, not a calibrated probability, and isn't presented as one in the UI.
- **Added a `/validate_photo` endpoint** rather than only catching a missing
  nail at the end of `/analyze` — waiting for both photos and a full analysis
  round trip just to find out the first photo was unusable was a worse user
  experience than catching it right after each capture, while the user is still
  standing in the same position holding the same pose.
- **Added a trained-CNN track and fused it with geometry** rather than relying on
  geometry alone. Geometry is precise but brittle (needs a clean side-profile
  contour); a CNN generalizes better to messy top-down photos. Fusing them — and
  returning *inconclusive* when they disagree — is more honest than trusting either
  in isolation, and never breaks the "never diagnose" rule.
- **Crop to the finger ROI before the CNN classifies.** Feeding the whole frame let
  the model key on background clutter; cropping with the same detector geometry uses
  aligns train/inference and was the single biggest real-world robustness gain.
- **Temperature-calibrated the CNN confidence** (fit on the validation set) so the
  "couldn't analyze" threshold gates on a meaningful probability, not raw softmax —
  important since over-confident wrong calls are exactly what a screener must avoid.
- **The CNN track is optional (lazy-loaded).** The Flask app must not hard-depend on
  torch; if weights/torch are absent the geometry track stands alone.
