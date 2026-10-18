"""Read-only exact-duplicate and Roboflow source-family audit of color_cls.

Exit 1 means cross-split connected groups; exit 2 means unreadable images.
No perceptual similarity or patient identity is inferred by this audit.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def source_family(filename):
    """Keep source namespace; remove crop index and final RF export suffix."""
    stem = Path(filename).stem
    if "__" not in stem:
        return None
    source, name = stem.split("__", 1)
    name = re.sub(r"__b\d+$", "", name)
    name = re.sub(r"(?:_(?:jpg|jpeg|png))?\.rf\.[0-9a-f]+$", "", name, flags=re.I)
    return source + "__" + name


def audit(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"Dataset directory does not exist: {root}")
    records, errors, buckets = [], [], defaultdict(list)
    for path in sorted(root.glob("*/*/*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        index = len(records)
        data = path.read_bytes()
        record = {"path": path.relative_to(root).as_posix(),
                  "split": path.parent.parent.name, "label": path.parent.name}
        records.append(record)
        buckets[("bytes", hashlib.sha256(data).hexdigest())].append(index)
        decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if decoded is None:
            errors.append(record["path"])
        else:
            pixel_key = hashlib.sha256(str((decoded.shape, decoded.dtype.str)).encode()
                                       + decoded.tobytes()).hexdigest()
            buckets[("pixels", pixel_key)].append(index)
        family = source_family(path.name)
        if family:
            buckets[("source_family", family)].append(index)

    parents = list(range(len(records)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for members in buckets.values():
        for index in members[1:]:
            parents[find(index)] = find(members[0])
    components = defaultdict(list)
    for index in range(len(records)):
        components[find(index)].append(index)
    evidence = defaultdict(set)
    for (kind, _), members in buckets.items():
        if len(members) > 1:
            evidence[find(members[0])].add(kind)
    groups = []
    for key, members in components.items():
        if len(members) < 2:
            continue
        splits = sorted({records[i]["split"] for i in members})
        labels = sorted({records[i]["label"] for i in members})
        groups.append({"members": [records[i] for i in members], "splits": splits,
                       "labels": labels, "cross_split": len(splits) > 1,
                       "label_conflict": len(labels) > 1, "evidence": sorted(evidence[key])})
    return {"root": str(root.resolve()), "images": len(records),
            "cross_split_groups": sum(g["cross_split"] for g in groups),
            "label_conflict_groups": sum(g["label_conflict"] for g in groups),
            "unreadable_images": errors, "groups": groups,
            "limitations": "Exact bytes, decoded pixels and filename source families only; does not rule out near-duplicates or shared patients. Source-family label conflicts can be legitimate multi-condition crops."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data/raw/color_cls")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = audit(args.root)
    encoded = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(encoded, encoding="utf-8")
        print(json.dumps({k: report[k] for k in ("images", "cross_split_groups", "label_conflict_groups", "unreadable_images")}))
    else:
        print(encoded)
    return 2 if report["unreadable_images"] else int(report["cross_split_groups"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
