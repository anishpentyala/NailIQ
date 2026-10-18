"""Build an isolated, permission-authorized candidate dataset; preserve source splits."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.audit_color_split_leakage import audit
from scripts.build_color_classification_dataset import bucket_split
from scripts.prepare_color_exclusions import build_exclusions

ARTHITAYA_LABELS = {
    "black line": "melanonychia", "white spot": "leukonychia",
    "onycholysis": "onycholysis", "beau_s line": "beaus_lines",
    "terry_s nail": "terrys_nails", "clubbing": "clubbing",
    "normal": "healthy", "mees_ line": "mees_lines",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=REPO / "data/raw/color_cls")
    parser.add_argument("--exclusions", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit("Output must be empty; existing datasets are preserved")
    args.out.mkdir(parents=True, exist_ok=True)
    old = json.loads(args.exclusions.read_text())
    excluded = set(old["excluded_crops"])
    rows = []

    def add(path, relative, source, group):
        if relative.as_posix() in excluded:
            return
        dest = args.out / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Copies prevent a future experiment from modifying the original dataset.
        shutil.copy2(path, dest)
        rows.append({"crop": relative.as_posix(), "source": path.relative_to(REPO).as_posix(),
                     "group": group, "source_name": source,
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    for path in sorted(args.base.glob("*/*/*")):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        relative = path.relative_to(args.base)
        if relative.as_posix() not in excluded:
            add(path, relative, "existing", None)
    root = REPO / "data/raw/nail-dataset-arthitaya/Nail"
    for class_name, label in ARTHITAYA_LABELS.items():
        for path in sorted((root / class_name).glob("*")):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            group = f"{class_name}-{path.stem}"
            split = bucket_split(group)  # preserve the historically used assignment
            name = re.sub(r"[^A-Za-z0-9]+", "_", group)
            add(path, Path(split) / label / ("arthitaya__" + name + path.suffix.lower()), "arthitaya", group)
    report = audit(args.out)
    if report["unreadable_images"]:
        raise RuntimeError(f"Unreadable images: {report['unreadable_images']}")
    quarantine = build_exclusions(args.out, report)
    quarantine["inherited_exclusions_sha256"] = hashlib.sha256(args.exclusions.read_bytes()).hexdigest()
    quarantine["excluded_source_paths"] = sorted({row["source"] for row in rows
        if row["crop"] in quarantine["excluded_crops"]})
    (args.out / "exclusions.json").write_text(json.dumps(quarantine, indent=2))
    (args.out / "split_audit.json").write_text(json.dumps(report, indent=2))
    counts = Counter("/".join(Path(row["crop"]).parts[:2]) for row in rows
                     if row["crop"] not in quarantine["excluded_crops"])
    manifest = {"rows": rows, "counts": dict(counts),
        "permission": {"knm": "User explicitly authorized use on 2026-10-01",
                       "arthitaya": "User explicitly confirmed permission on 2026-10-01; not a claim of public CC licensing"},
        "label_status": "Inherited community labels; no clinical adjudication",
        "test_status": "Original split assignments retained; previous TEST inspection remains historical",
        "limitations": "Exact duplicates and filename families checked; patient independence and near-duplicates are not fully established"}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"counts": dict(counts), "new_quarantine": len(quarantine["excluded_crops"])}), flush=True)


if __name__ == "__main__":
    main()
