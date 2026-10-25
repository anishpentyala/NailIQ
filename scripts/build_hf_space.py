"""Assemble a clean upload folder for a Hugging Face Docker Space (./hf_space_build, gitignored).

Run from the repo root after `npm --prefix frontend run build`:
    backend/venv/Scripts/python.exe scripts/build_hf_space.py [--include-models]
Default: TWO folders. hf_space_build/ is code only (public Space) and hf_models_build/ holds the weights (private model
repo the Space downloads at startup, see deploy/hf_space/fetch_models.py), so the public repo never contains the weights.
--include-models bundles the weights into the Space folder instead (they become publicly downloadable; read
docs/MODEL_LICENSES.md first). Only the model files the running app actually loads are copied (about 210 MB).
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hf_space_build"
OUT_MODELS = ROOT / "hf_models_build"
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

    for name in ("Dockerfile", "requirements.txt", "README.md", "fetch_models.py"):
        shutil.copy(ROOT / "deploy" / "hf_space" / name, OUT / name)
    (OUT / ".dockerignore").write_text("**/__pycache__\n*.pyc\n", encoding="utf-8")

    shutil.copytree(dist, OUT / "frontend" / "dist")
    for f in ("app.py", "models.py"):
        (OUT / "backend").mkdir(exist_ok=True)
        shutil.copy(ROOT / "backend" / f, OUT / "backend" / f)
    shutil.copytree(ROOT / "ml" / "infer", OUT / "ml" / "infer",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    (OUT / "ml" / "__init__.py").write_text("", encoding="utf-8")
    include = "--include-models" in sys.argv
    models_dir = (OUT / "ml" / "models") if include else OUT_MODELS
    if OUT_MODELS.exists():
        shutil.rmtree(OUT_MODELS)
    models_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in model_files():
        src = MODELS / f
        if not src.exists():
            sys.exit(f"missing model file: {src}")
        shutil.copy(src, models_dir / f)
        total += src.stat().st_size
    if not include:
        (OUT / "ml" / "models").mkdir(parents=True)  # filled at startup by fetch_models.py
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT} ({size / 1e6:.1f} MB, code only)" if not include else f"built {OUT} ({size / 1e6:.0f} MB incl. models)")
    if not include:
        print(f"built {OUT_MODELS} ({total / 1e6:.0f} MB of weights; upload to a PRIVATE model repo)")


if __name__ == "__main__":
    main()
