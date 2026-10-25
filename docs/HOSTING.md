# Hosting NailIQ on a Hugging Face Space (free CPU, public link)

What this gives judges: one https link (works in iPhone Safari, Add to Home Screen) that runs the real models.
Photos are analyzed in memory and never saved; History is per browser (anonymous random id) and resets when the Space restarts.

## Build the upload folders (on this PC, repo root)
    npm --prefix frontend run build
    backend/venv/Scripts/python.exe scripts/build_hf_space.py
-> `hf_space_build/` (about 8 MB, **code only**, goes in the PUBLIC Space) and `hf_models_build/` (about 210 MB of weights, goes in a
PRIVATE model repo). Decision 2026-10-24 (docs/MODEL_LICENSES.md, option A): the weights are never public. At startup the Space
runs `fetch_models.py`, which downloads them from the private repo using a token stored as a Space secret.

The server code path and the download step were tested locally (stubbed download); the Docker image itself has NOT been built here
(no Docker on this PC), so the first Space build is the real test.

## One-time setup (you; needs your Hugging Face account - never paste your token into chat or into files)
1. Create a read token: huggingface.co -> Settings -> Access Tokens -> New token. Fine-grained is best: read access to the model repo only.
2. Create the private model repo and upload the weights:
       pip install -U huggingface_hub
       hf auth login                      (paste your own write token when asked)
       hf upload <your-username>/nailiq-models hf_models_build . --repo-type=model --private
3. Create the Space: New Space -> name `nailiq`, SDK **Docker** (blank), **CPU basic (free)**, **Public**.
4. In the Space -> Settings: add a **Variable** `NAILIQ_MODELS_REPO` = `<your-username>/nailiq-models`
   and a **Secret** `HF_TOKEN` = the read token from step 1.
5. Upload the code: drag the *contents* of `hf_space_build/` into the Space's Files tab, or
       hf upload <your-username>/nailiq hf_space_build . --repo-type=space
6. Watch the Logs tab (first build takes several minutes: PyTorch). You should see `[models] downloaded 13 files`. When it says Running, open
   https://<your-username>-nailiq.hf.space . If it stops with a `[models] ...` message, that variable or secret is missing/wrong.

## Before judges look
- Free Spaces sleep after a while idle and take about a minute to wake: open the link yourself a few minutes before.
- Test one real scan from your iPhone on the Space link (camera needs https, which the Space provides).
- Put the link and a demo video in the submission. Say plainly: screener, never a diagnosis, accuracy on phone photos not measured.

## Things to know
- Anyone with the link can use it (and send photos). The README on the Space states that photos are not saved.
- Model weights stay private (see above); the Space README credits the datasets (CC BY needs attribution). The Arthitaya Kaggle set has no
  stated license (docs/MODEL_LICENSES.md): keeping the weights private is the mitigation, not a resolution.
- Do not add the weights, `ml/models`, or any dataset images to the public Space.
- Configuration is in `deploy/hf_space/Dockerfile` (env: NAILIQ_REQUIRE_CLIENT_ID, NAILIQ_TRUST_PROXY, NAILIQ_STATIC_DIR).
