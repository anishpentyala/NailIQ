# Hosting NailIQ on a Hugging Face Space (free CPU, public link)

What this gives judges: one https link (works in iPhone Safari, Add to Home Screen) that runs the real models.
Photos are analyzed in memory and never saved; History is per browser (anonymous random id) and resets when the Space restarts.

## Build the upload folder (on this PC, repo root)
    npm --prefix frontend run build
    backend/venv/Scripts/python.exe scripts/build_hf_space.py      # -> hf_space_build/ (about 218 MB)

The server code path was tested from that folder (serves the web app, real findings, per-client History). The Docker
image itself has NOT been built here (no Docker on this PC), so the first Space build is the real test.

## One-time setup (you; needs your Hugging Face account)
1. huggingface.co -> New Space -> name `nailiq`, SDK **Docker** (blank template), hardware **CPU basic (free)**, visibility **Public**.
2. Upload the folder. Either drag the *contents* of `hf_space_build/` into the Space's Files tab, or:
       pip install -U huggingface_hub
       hf auth login                      (paste your own write token; never share it)
       hf upload <your-username>/nailiq hf_space_build . --repo-type=space
3. Watch the Space's Logs tab. The first build takes several minutes (installs PyTorch). When it says Running, open
   https://<your-username>-nailiq.hf.space

## Before judges look
- Free Spaces sleep after a while idle and take about a minute to wake: open the link yourself a few minutes before.
- Test one real scan from your iPhone on the Space link (camera needs https, which the Space provides).
- Put the link and a demo video in the submission. Say plainly: screener, never a diagnosis, accuracy on phone photos not measured.

## Things to know
- Anyone with the link can use it (and send photos). The README on the Space states that photos are not saved.
- Model weights are uploaded with the Space. Check the training-data licenses (see ATTRIBUTION.md / data/raw/LICENSES.md)
  allow publishing trained weights before making the Space public - this has not been verified.
- Configuration is in `deploy/hf_space/Dockerfile` (env: NAILIQ_REQUIRE_CLIENT_ID, NAILIQ_TRUST_PROXY, NAILIQ_STATIC_DIR).
