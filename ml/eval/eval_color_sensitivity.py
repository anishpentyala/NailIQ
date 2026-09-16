"""Real end-to-end SENSITIVITY (recall) test through /analyze -- the counterpart to
fp_rate-style false-positive checks (see this file's history / CLAUDE.md). Every other
color-track eval (eval_color_ensemble.py, calibrate_color.py) measures the CNN in
isolation on pre-cropped nail-plate images -- that skips region detection, the bbox
crop, and color_fusion entirely. This script runs known-positive FULL images through
the actual Flask /analyze endpoint, with the same realistic-framing simulation used to
test false positives, so the reported recall is the number a real user would see.

Critically, this only draws from the SAME held-out test split that
ml/eval/eval_color_ensemble.py reports on: it replicates scripts/build_color_
classification_dataset.py's exact split logic (bucket_split / KNM's own shipped split)
over the ORIGINAL, uncropped source images, so these are genuinely held-out, not
train-leaked, and comparable to the CNN-only numbers.

data/raw/nail-disease (used to supply leukonychia/onycholysis/splinter_hemorrhages/
lindsays_nails positives here) was REMOVED 2026-09 after a watermark audit found
visually-confirmed stock-photo watermarks in it -- see scripts/build_color_
classification_dataset.py's module docstring. This script no longer draws from it, for
the same provenance reason, not just the training-side licensing concern: measuring
"recall" against images that may not even be genuine nail photos isn't a real number.
chaa (data/raw/yolov8-nails-segmentation-ckvkd) replaces it for splinter_hemorrhages;
leukonychia, onycholysis and lindsays_nails currently have no vetted source and are
absent from `positives` entirely rather than measured against a) an image confirmedly
contaminated or b) with a silent zero -- see CLAUDE.md for what that means for those
three conditions' validation status.

    cd <repo root>
    backend/venv/Scripts/python.exe ml/eval/eval_color_sensitivity.py

Findings from the first run (see CLAUDE.md) were substantially worse than the
CNN-only precision/recall numbers for several conditions -- confidence floors tuned
against the isolated CNN throw away many true positives once region-detection/bbox-crop
noise and the classical heuristic's own weakness are folded back in. Re-run this after
any retrain or threshold change; test-set-only numbers are not the real story.
"""
import base64
import os
import hashlib
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import yaml

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

_scratch_db = Path(tempfile.gettempdir()) / "nailiq_eval_color_sensitivity.db"
# must be set before importing app (Flask-SQLAlchemy builds the engine at import)
os.environ["NAILIQ_DATABASE_URI"] = "sqlite:///" + str(_scratch_db).replace("\\", "/")
import app as app_module  # noqa: E402

app_module._rate_limited = lambda ip: False  # test client shares one IP; not a real client
with app_module.app.app_context():
    app_module.db.create_all()
client = app_module.app.test_client()

SPLITS = ("train", "valid", "test")

KNM = REPO / "data" / "raw" / "nail-disease-detection-mxoqy"
CHAA = REPO / "data" / "raw" / "yolov8-nails-segmentation-ckvkd"
GHANA = REPO / "data" / "raw" / "fingernails-ghana-anemia" / "Fingernails"
ARTHITAYA = REPO / "data" / "raw" / "nail-dataset-arthitaya" / "Nail"

# Must mirror scripts/build_color_classification_dataset.py's CLASS_SLUGS / CHAA_SLUGS /
# ARTHITAYA_SLUGS -- only the app-reported conditions are needed here (discrimination-only
# classes like melanoma/koilonychia/clubbing are irrelevant to a recall check, though
# chaa's koilonychia entry is skipped below for the same reason).
KNM_SLUGS = {
    "Beaus Line": "beaus_lines",
    "Blue Finger": "cyanosis",
    "Muehrckes Lines": "muehrckes_lines",
    "Pitting": "pitting",
    "Terry-s Nail": "terrys_nails",
}
CHAA_SLUGS = {
    "Splinter Hemorrhage": "splinter_hemorrhages",
    "Terry-s nail": "terrys_nails",
}
ARTHITAYA_SLUGS = {
    "black line": "melanonychia",
    "beau_s line": "beaus_lines",
    "terry_s nail": "terrys_nails",
    "onycholysis": "onycholysis",
    "white spot": "leukonychia",
}
_ANEMIC_TOKENS = ("anemic", "anaemic", "pallor")


def bucket_split(key):
    """Same deterministic md5-based split as build_color_classification_dataset.py."""
    bucket = int(hashlib.md5(key.encode()).hexdigest(), 16) % 10
    return "train" if bucket < 8 else "valid" if bucket == 8 else "test"


def ghana_label(name):
    s = name.lower()
    if s.startswith("non") or "non-" in s or "non " in s:
        return "healthy"
    if any(tok in s for tok in _ANEMIC_TOKENS):
        return "pallor"
    return None


def ghana_patient_key(name, label):
    m = re.search(r"\d+", name)
    pid = m.group(0).lstrip("0") or "0" if m else "x"
    return f"{label}-{pid}"


def load_names(root):
    return yaml.safe_load((root / "data.yaml").read_text())["names"]


def find_image_file(label_path):
    images_dir = label_path.parent.parent / "images"
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = images_dir / (label_path.stem + ext)
        if candidate.exists():
            return candidate
    return None


def gather_positives():
    """Return {slug: [full_image_path, ...]} using only TEST-split images."""
    positives = defaultdict(list)

    # KNM keeps its own shipped split -- its `test` folder IS the held-out test set.
    if KNM.exists():
        names = load_names(KNM)
        idx_to_slug = {i: KNM_SLUGS[n] for i, n in enumerate(names) if n in KNM_SLUGS}
        labels_dir = KNM / "test" / "labels"
        for label_file in sorted(labels_dir.glob("*.txt")):
            slugs_here = {idx_to_slug.get(int(p.split()[0])) for p in label_file.read_text().splitlines()
                          if len(p.split()) == 5 and idx_to_slug.get(int(p.split()[0]))}
            if slugs_here:
                img = find_image_file(label_file)
                if img:
                    for slug in slugs_here:
                        positives[slug].append(img)

    # chaa was re-split by image stem via bucket_split (ingest_yolo resplit=True). Its
    # labels are YOLO segmentation polygons (class + variable-length x/y list), not
    # fixed 5-field detection boxes like KNM, so the row filter below is `>= 5` (has a
    # class index plus at least one point), not `== 5`.
    if CHAA.exists():
        names = load_names(CHAA)
        idx_to_slug = {i: CHAA_SLUGS[n] for i, n in enumerate(names) if n in CHAA_SLUGS}
        for src_split in SPLITS:
            labels_dir = CHAA / src_split / "labels"
            if not labels_dir.exists():
                continue
            for label_file in sorted(labels_dir.glob("*.txt")):
                if bucket_split(label_file.stem) != "test":
                    continue
                slugs_here = {idx_to_slug.get(int(p.split()[0])) for p in label_file.read_text().splitlines()
                              if len(p.split()) >= 5 and idx_to_slug.get(int(p.split()[0]))}
                if slugs_here:
                    img = find_image_file(label_file)
                    if img:
                        for slug in slugs_here:
                            positives[slug].append(img)

    # Ghana: pallor, re-split by patient key (add_ghana's grouping)
    if GHANA.exists():
        for img_path in sorted(GHANA.glob("*.png")):
            if ghana_label(img_path.name) != "pallor":
                continue
            if bucket_split(ghana_patient_key(img_path.name, "pallor")) != "test":
                continue
            positives["pallor"].append(img_path)

    # arthitaya: melanonychia + a few others, re-split by "<class>-<stem>" (add_arthitaya)
    if ARTHITAYA.exists():
        for cls_dir in sorted(ARTHITAYA.iterdir()):
            slug = ARTHITAYA_SLUGS.get(cls_dir.name) if cls_dir.is_dir() else None
            if slug is None:
                continue
            for img_path in sorted(cls_dir.iterdir()):
                if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                    continue
                if bucket_split(f"{cls_dir.name}-{img_path.stem}") != "test":
                    continue
                positives[slug].append(img_path)

    return positives


def b64(path):
    """Simulate realistic phone framing: downscale + gray border, same as the
    false-positive check, so results are comparable to that measurement."""
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    scale = max(1.0, 480 / max(h, w))
    if scale > 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    pad = int(0.3 * max(img.shape[:2]))
    img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(45, 45, 45))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return base64.b64encode(buf.tobytes()).decode()


def main():
    positives = gather_positives()
    healthy_dir = REPO / "data" / "raw" / "merged" / "test" / "healthy"
    side = b64(sorted(healthy_dir.glob("*.jpg"))[0])

    print("positive TEST-split images found per condition:")
    for slug in sorted(positives):
        print(f"  {slug:22s} n={len(positives[slug])}")
    print()

    results = {}
    reject_reasons = Counter()
    for slug, paths in sorted(positives.items()):
        detected = missed = rejected = 0
        examples = []
        for p in paths:
            top = b64(p)
            if top is None:
                continue
            resp = client.post("/analyze", json={"side_image": side, "top_image": top})
            if resp.status_code != 200:
                rejected += 1
                reject_reasons[f"http_{resp.status_code}"] += 1
                continue
            findings = [f for f in resp.get_json()["findings"] if f["label"] == slug]
            if not findings:
                rejected += 1
                continue
            f = findings[0]
            if f["verdict"] == "inconclusive":
                rejected += 1
                reject_reasons[f.get("failure_reason") or "inconclusive_other"] += 1
            elif f["verdict"] == "outside":
                detected += 1
            else:  # "within" -- a real positive the pipeline called healthy: a MISS
                missed += 1
                examples.append(p.name)
        results[slug] = (detected, missed, rejected, len(paths))
        print(f"{slug:22s} detected={detected:3d}  missed={missed:3d}  "
              f"rejected/inconclusive={rejected:3d}  (n={len(paths)})")
        if examples:
            print(f"    missed examples: {examples[:5]}")

    print("\nreject/inconclusive reasons across all conditions:")
    for reason, n in reject_reasons.most_common():
        print(f"  {reason}: {n}")

    print("\nsensitivity (recall) among ANALYZABLE positives only:")
    for slug, (det, miss, rej, total) in sorted(results.items()):
        analyzable = det + miss
        rate = det / analyzable if analyzable else float("nan")
        print(f"  {slug:22s} {rate:.1%}  ({det}/{analyzable} analyzable, {rej} rejected)")


if __name__ == "__main__":
    main()
