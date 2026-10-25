"""Assemble everything the browser needs to run NailIQ's AI on the user's own device.

Writes frontend/public/ondevice/ (gitignored; ~230 MB):
  models/   the ONNX networks + manifests         (run scripts/export_onnx.py first)
  py/       ml_bundle.zip: ml/infer/*.py (the exact analysis code the server uses) + manifests
  pyodide/  self-hosted Pyodide runtime + numpy, opencv-python, pillow wheels
  ort/      onnxruntime-web (WebAssembly)
  manifest.json  every file with its size, so the worker can show download progress and cache by version

Run from the repo root:  ml/venv/Scripts/python.exe scripts/build_ondevice.py
Downloads use 8 parallel connections and skip files that are already complete.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "ondevice"
MODELS_SRC = ROOT / "deploy" / "ondevice" / "models"
PYODIDE_VERSION = "0.27.7"
CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
CORE = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
PACKAGES = ["numpy", "opencv-python", "pillow"]
ORT_DIST = ROOT / "frontend" / "node_modules" / "onnxruntime-web" / "dist"
ORT_FILES = ["ort.wasm.min.js", "ort-wasm-simd-threaded.wasm", "ort-wasm-simd-threaded.mjs"]
MANIFEST_JSON = ["nail_classifier_labels.json", "nail_color_classifier_labels.json"]


def download(files, dest):
    dest.mkdir(parents=True, exist_ok=True)
    todo = [f for f in files if not (dest / f).exists()]
    if not todo:
        return
    cmd = ["curl", "-sSfL", "--parallel", "--parallel-max", "8", "--retry", "3"]
    for f in todo:
        cmd += ["-o", str(dest / (f + ".part")), CDN + f]
    subprocess.run(cmd, check=True)
    for f in todo:
        (dest / (f + ".part")).rename(dest / f)


def wheel_closure(lock):
    pkgs, stack = {}, list(PACKAGES)
    while stack:
        name = stack.pop()
        if name in pkgs:
            continue
        pkgs[name] = lock["packages"][name]
        stack.extend(pkgs[name].get("depends", []))
    return pkgs


def main():
    if not any(MODELS_SRC.glob("*.onnx")):
        sys.exit("No ONNX models: run scripts/export_onnx.py first")
    OUT.mkdir(parents=True, exist_ok=True)

    # models
    models = OUT / "models"
    models.mkdir(exist_ok=True)
    for src in MODELS_SRC.glob("*.onnx"):
        if not (models / src.name).exists() or (models / src.name).stat().st_size != src.stat().st_size:
            shutil.copy(src, models / src.name)

    # python bundle: the real analysis code + the small manifests it reads from ml/models
    py = OUT / "py"
    py.mkdir(exist_ok=True)
    with zipfile.ZipFile(py / "ml_bundle.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ml/__init__.py", "")
        for f in sorted((ROOT / "ml" / "infer").glob("*.py")):
            z.write(f, f"ml/infer/{f.name}")
        for name in MANIFEST_JSON:
            z.write(MODELS_SRC / name, f"ml/models/{name}")
        for f in sorted(MODELS_SRC.glob("*_specialist.json")):
            z.write(f, f"ml/models/{f.name}")

    # pyodide runtime
    pyo = OUT / "pyodide"
    download(CORE, pyo)
    lock = json.loads((pyo / "pyodide-lock.json").read_text())
    wheels = [p["file_name"] for p in wheel_closure(lock).values()]
    download(wheels, pyo)

    # onnxruntime-web
    ort = OUT / "ort"
    ort.mkdir(exist_ok=True)
    for f in ORT_FILES:
        shutil.copy(ORT_DIST / f, ort / f)

    files = {}
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files[p.relative_to(OUT).as_posix()] = p.stat().st_size
    digest = hashlib.sha1(json.dumps(files, sort_keys=True).encode()).hexdigest()[:12]
    (OUT / "manifest.json").write_text(json.dumps({
        "version": digest, "pyodide": PYODIDE_VERSION, "packages": PACKAGES,
        "models": sorted(f.name for f in models.glob("*.onnx")), "files": files}, indent=1))
    print(f"ok: {len(files)} files, {sum(files.values()) / 1e6:.0f} MB, version {digest}")


if __name__ == "__main__":
    main()
