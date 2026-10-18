"""Find cross-split dHash candidates for inspection; similarity is not proof."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import defaultdict

import cv2


def difference_hash(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    value = 0
    for bit in (small[:, 1:] > small[:, :-1]).flat:
        value = (value << 1) | int(bit)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--distance", type=int, default=2)
    parser.add_argument("--exclusions", type=Path)
    args = parser.parse_args()
    exclusions = set(json.loads(args.exclusions.read_text())["excluded_crops"]) if args.exclusions else set()
    records, hashes = [], defaultdict(list)
    for path in sorted(args.root.glob("*/*/*")):
        relative = path.relative_to(args.root).as_posix()
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"} or relative in exclusions:
            continue
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f"Unreadable image: {path}")
        value = difference_hash(image)
        index = len(records)
        records.append({"path": relative, "split": path.parent.parent.name,
                        "label": path.parent.name, "dhash": f"{value:016x}"})
        hashes[path.parent.parent.name].append((value, index))
    pairs = []
    splits = sorted(hashes)
    for i, split in enumerate(splits):
        for other in splits[i + 1:]:
            for a, index_a in hashes[split]:
                for b, index_b in hashes[other]:
                    distance = (a ^ b).bit_count()
                    if distance <= args.distance:
                        pairs.append({"a": index_a, "b": index_b, "distance": distance})
    pairs.sort(key=lambda p: (p["distance"], records[p["a"]]["path"], records[p["b"]]["path"]))
    report = {"images": len(records), "max_distance": args.distance,
              "exclusions_sha256": hashlib.sha256(args.exclusions.read_bytes()).hexdigest() if args.exclusions else None,
              "status": "unverified similarity candidates; do not equate with confirmed duplicates",
              "records": records, "pairs": pairs}
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps({"images": len(records), "candidate_pairs": len(pairs),
                      "cross_label_pairs": sum(records[p["a"]]["label"] != records[p["b"]]["label"] for p in pairs)}))


if __name__ == "__main__":
    main()
