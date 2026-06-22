# Lovibond

A precautionary screener for digital clubbing — a physical sign present in ~35% of
non-small-cell lung cancer cases, also linked to heart disease, COPD, and liver
disease. Clubbing develops slowly and is rarely self-noticed. Lovibond lets anyone
photograph their finger in profile and get a quick, honest read on whether their nail
angle is worth mentioning to a doctor.

**This is not a diagnostic tool.** It never says "you have cancer" or "you have
clubbing." It says whether a measured angle is inside or outside the typical range,
and always recommends following up with a doctor. See `CRITICAL PRODUCT RULE` in the
project brief — every screen must carry this framing.

## Status

Steps 1–2 of the build are complete: full repo scaffold, and a working
camera → backend → result loop using a hardcoded backend response. Real CV (Track A
geometric, Track B classifier) comes next.

## Repo layout

```
frontend/   Vite + React. Mobile-first camera capture UI.
backend/    Flask REST API. Single /analyze endpoint (base64 in, JSON out).
ml/         Training scripts + inference modules for the CV models.
  train/    Model training scripts (Track B classifier, etc.)
  infer/    Inference wrappers used by the backend.
  models/   Saved model weights (gitignored — large binaries).
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

Runs on `http://localhost:5000`. `/analyze` currently returns a hardcoded stub
response — no real model is wired in yet.

### Frontend (Vite + React)

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` (Vite default). Opens the camera, captures a frame on
button press, POSTs it to the backend, and renders the result.

**Camera permissions**: most browsers require HTTPS or `localhost` for
`getUserMedia`. `localhost` is fine for local dev; testing on a phone over LAN will
need a tunnel (e.g. `ngrok`) or a dev cert.

## API contract

`POST /analyze`

Request:
```json
{ "image": "<base64-encoded JPEG/PNG, no data: prefix needed>" }
```

Response:
```json
{
  "angle": 165.0,
  "verdict": "within" | "outside",
  "confidence": 0.0,
  "track_used": "stub" | "classifier" | "geometric"
}
```

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
