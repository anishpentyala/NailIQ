"""Assemble a clean upload folder for a Hugging Face Docker Space (./hf_space_build, gitignored).

Run from the repo root after `npm --prefix frontend run build`:
    backend/venv/Scripts/python.exe scripts/build_hf_space.py
Then upload the folder's contents to the Space (see docs/HOSTING.md). Only the model files the running app actually
loads are copied (about 210 MB); the rest of ml/models is experiments and held-out evaluation models.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hf_space_build"
MODELS = ROOT / "ml" / "models"

# ml/infer/specialists.py ENABLED, plus the two CNN ensembles named in their manifests and the orientation model
SPECIALISTS = ("onycholysis", "leukonychia", "beaus_lines")


def model_files():
    files = ["nail_classifier_labels.json", "nail_color_classifier_labels.json", "nail_orientation_resnet18.pt"]
    for manifest in ("nail_classifier_labels.json", "nail_color_classifier_labels.json"):
        meta = json.loads((MODELS / manifest).read_text(encoding="utf-8"))
        files += [m["weights_file"] for m in meta.get("ensemble", [])]
    for sign in SPECIALISTS:
        files += [f"{sign}_specialist.pt", f"{sign}_specialist.json"]
    for optional in ("nail_locator.json", "nail_locator.pt"):  # not present in this checkout; copied if it ever is
        if (MODELS / optional).exists():
            files.append(optional)
    return files


def main():
    dist = ROOT / "frontend" / "dist"
    if not (dist / "index.html").exists():
        sys.exit("frontend/dist missing: run `npm --prefix frontend run build` first")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    for name in ("Dockerfile", "requirements.txt", "README.md"):
        shutil.copy(ROOT / "deploy" / "hf_space" / name, OUT / name)
    (OUT / ".dockerignore").write_text("**/__pycache__\n*.pyc\n", encoding="utf-8")

    shutil.copytree(dist, OUT / "frontend" / "dist")
    for f in ("app.py", "models.py"):
        (OUT / "backend").mkdir(exist_ok=True)
        shutil.copy(ROOT / "backend" / f, OUT / "backend" / f)
    shutil.copytree(ROOT / "ml" / "infer", OUT / "ml" / "infer",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    (OUT / "ml" / "__init__.py").write_text("", encoding="utf-8")
    (OUT / "ml" / "models").mkdir(parents=True)
    total = 0
    for f in model_files():
        src = MODELS / f
        if not src.exists():
            sys.exit(f"missing model file: {src}")
        shutil.copy(src, OUT / "ml" / "models" / f)
        total += src.stat().st_size
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT} ({size / 1e6:.0f} MB; models {total / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
