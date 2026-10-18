"""Quarantine known cross-split families without moving or deleting images."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.audit_color_split_leakage import audit, source_family


def patient_key(relative):
    path = Path(relative)
    if not path.name.startswith("ghana__"):
        return None
    match = re.search(r"\d+", path.name.split("__", 1)[1])
    return f"ghana:{path.parent.name}:{int(match.group())}" if match else None


def build_exclusions(root, report, reviewed_pairs=None):
    files = sorted(p for p in root.glob("*/*/*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    paths = {p.relative_to(root).as_posix(): p for p in files}
    excluded = {m["path"] for g in report["groups"] if g["cross_split"] for m in g["members"]}
    for pair in reviewed_pairs or []:
        if pair.get("decision") != "confirmed_duplicate":
            continue
        for path in (pair["a"], pair["b"]):
            if path not in paths:
                raise ValueError(f"Reviewed duplicate does not exist in dataset: {path}")
            excluded.add(path)
    while True:
        old = set(excluded)
        patients = {patient_key(p) for p in excluded} - {None}
        families = {source_family(Path(p).name) for p in excluded} - {None}
        excluded.update(p for p in paths if patient_key(p) in patients or source_family(Path(p).name) in families)
        for group in report["groups"]:
            members = {m["path"] for m in group["members"]}
            if members & excluded:
                excluded.update(members)
        if old == excluded:
            break
    fingerprint = hashlib.sha256()
    for relative, path in paths.items():
        fingerprint.update(relative.encode())
        fingerprint.update(hashlib.sha256(path.read_bytes()).digest())
    return {"schema_version": 1, "dataset_fingerprint": fingerprint.hexdigest(),
            "excluded_crops": sorted(excluded),
            "excluded_families": sorted({source_family(Path(p).name) for p in excluded} - {None}),
            "excluded_patient_keys": sorted({patient_key(p) for p in excluded} - {None}),
            "counts_by_split": dict(Counter(Path(p).parts[0] for p in excluded)),
            "reviewed_pairs": reviewed_pairs or [],
            "limitations": report["limitations"],
            "reason": "Cross-split byte/pixel duplicates or filename-family candidates; expanded to linked Ghana patient groups. No split reassignment."}


def excludes_source(path, manifest):
    """Reproduce builder naming to match full-image evaluation with crop quarantine."""
    parts = path.parts
    relative = path.as_posix()
    try:
        relative = path.relative_to(REPO).as_posix()
    except ValueError:
        pass
    if relative in manifest.get('excluded_source_paths', []):
        return True
    if 'nail-dataset-arthitaya' in parts:
        group = f'{path.parent.name}-{path.stem}'
        name = 'arthitaya__' + re.sub(r'[^A-Za-z0-9]+', '_', group) + path.suffix.lower()
    elif "fingernails-ghana-anemia" in parts:
        name = "ghana__" + re.sub(r"[^A-Za-z0-9]+", "_", path.stem) + ".jpg"
    else:
        sources = {"nail-disease-detection-mxoqy": "knm", "yolov8-nails-segmentation-ckvkd": "chaa",
                   "anemia-nails-detection": "anemia", "nail-disease-classification-nihati": "nihati"}
        prefix = next((prefix for folder, prefix in sources.items() if folder in parts), None)
        if prefix is None:
            return False
        name = prefix + "__" + path.name
    return source_family(name) in manifest.get("excluded_families", [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO / "data/raw/color_cls")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reviewed-pairs", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    if report["unreadable_images"]:
        raise SystemExit("Unreadable dataset images; fix before preparing exclusions")
    reviewed_pairs = json.loads(args.reviewed_pairs.read_text()) if args.reviewed_pairs else None
    manifest = build_exclusions(args.root, report, reviewed_pairs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"excluded": len(manifest["excluded_crops"]), "by_split": manifest["counts_by_split"]}))


if __name__ == "__main__":
    main()
