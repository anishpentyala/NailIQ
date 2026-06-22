# Lovibond

A precautionary screener for nail-based signs of systemic disease. Digital clubbing
is present in ~35% of non-small-cell lung cancer cases and is also linked to heart
disease, COPD, and liver disease; koilonychia (spoon nails) is linked to iron
deficiency anemia. Both develop slowly and are rarely self-noticed. Lovibond lets
anyone photograph their finger and get a quick, honest read on whether their nail
signs are worth mentioning to a doctor.

**This is not a diagnostic tool.** It never names a disease or says "you have
clubbing." Each finding is only ever "within typical range," "outside typical
range," or "couldn't analyze this photo" — and always recommends following up with a
doctor. Every screen carries this framing.

## Status

Real classical CV is wired in for two findings, both derived from a single
side-profile photo: **clubbing** (Lovibond angle, via contour geometry + cosine
rule) and **koilonychia** (nail-plate curvature, via contour sagitta). A second,
top-down photo is captured and sent to the backend but not analyzed yet — reserved
for color/texture-based findings (leukonychia, splinter hemorrhages, Terry's nails)
planned for later. See `ml/infer/` for the pipeline.

## Repo layout

```
frontend/   Vite + React. Mobile-first, two-step camera capture UI.
backend/    Flask REST API. Single /analyze endpoint (base64 in, JSON out).
ml/         Training scripts + inference modules for the CV models.
  train/    Model training scripts (future: Track B classifier).
  infer/    Classical CV pipeline (preprocessing, keypoints, per-condition
            measurement, orchestrator) — no trained model, no dataset needed.
  models/   Saved model weights (gitignored — large binaries; unused for now).
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

## API contract

`POST /analyze`

Request:
```json
{
  "side_image": "<base64-encoded JPEG/PNG, no data: prefix needed>",
  "top_image": "<base64-encoded JPEG/PNG>"
}
```
`side_image` is analyzed now. `top_image` is required by the contract (so the
capture flow doesn't need to change again) but is currently decoded and discarded —
reserved for color/texture-based findings later.

Response:
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
      "track_used": "geometric",
      "failure_reason": null
    },
    {
      "label": "koilonychia",
      "display_name": "Nail curvature (koilonychia)",
      "value": null,
      "unit": null,
      "verdict": "within" | "outside" | "inconclusive",
      "confidence": 0.7,
      "track_used": "geometric",
      "failure_reason": null
    }
  ]
}
```
`inconclusive` means the contour/keypoint pipeline couldn't reliably locate the
finger or its keypoints (bad lighting, busy background, finger cropped out of
frame) — `failure_reason` names the specific check that failed. This is distinct
from "within"/"outside": it never guesses a verdict it isn't confident in.
`confidence` is a heuristic derived from keypoint-detection quality (tip
sharpness, cuticle curvature clarity), not a statistically calibrated probability.

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
