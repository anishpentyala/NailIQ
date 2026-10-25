"""Download the model weights from a PRIVATE Hugging Face model repo at startup.

The public Space repository contains code only, so nobody can download the trained weights from it. The Space needs:
  variable NAILIQ_MODELS_REPO  e.g. your-username/nailiq-models   (the private model repo)
  secret   HF_TOKEN            a read token that can read that repo
If the weights are already present (a build that bundled them) nothing is downloaded.
"""
import os
import sys
from pathlib import Path

REQUIRED = ("nail_classifier_labels.json", "nail_color_classifier_labels.json")


def main(download=None, dest=None):
    dest = Path(dest) if dest else Path(__file__).resolve().parent / "ml" / "models"
    if all((dest / f).exists() for f in REQUIRED):
        print("[models] already present, skipping download")
        return
    repo, token = os.environ.get("NAILIQ_MODELS_REPO"), os.environ.get("HF_TOKEN")
    if not repo:
        sys.exit("[models] NAILIQ_MODELS_REPO is not set (Space variable, e.g. your-username/nailiq-models)")
    if not token:
        sys.exit("[models] HF_TOKEN is not set (Space secret: a read token for the private model repo)")
    if download is None:
        from huggingface_hub import snapshot_download as download
    dest.mkdir(parents=True, exist_ok=True)
    download(repo_id=repo, repo_type="model", token=token, local_dir=str(dest))
    missing = [f for f in REQUIRED if not (dest / f).exists()]
    if missing:
        sys.exit(f"[models] downloaded repo {repo} but these files are missing: {missing}")
    print(f"[models] downloaded {sum(1 for p in dest.iterdir() if p.is_file())} files from {repo}")


if __name__ == "__main__":
    main()
