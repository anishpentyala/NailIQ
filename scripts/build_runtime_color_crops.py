"""Create experimental TRAIN/VALID crops using the production localization path.

Source labels are inherited, not clinically re-verified. Multi-label source images
are skipped to avoid forcing them into a single-label classifier. Never reads TEST.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_end_to_end import gather
from ml.eval.eval_color_sensitivity import b64
from ml.infer import nail_region
from ml.infer.color_classifier import _crop_to_bbox
from ml.infer.preprocessing import decode_base64_image, extract_best_contour, focus_score, is_flat_frame
from ml.infer.pipeline import BLUR_THRESHOLD
import cv2


def runtime_crop(path):
    encoded = b64(path)
    image = decode_base64_image(encoded) if encoded else None
    if image is None:
        return None, "unreadable"
    if is_flat_frame(image):
        return None, "camera_feed_blank"
    if focus_score(image) < BLUR_THRESHOLD:
        return None, "too_blurry"
    contour, validation = extract_best_contour(image)
    if not validation["is_valid"]:
        return None, validation["reason"]
    region, reason = nail_region.compute_nail_region(image, contour)
    if reason:
        return None, reason
    return _crop_to_bbox(image, region["bbox_norm"]), None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--exclusions", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit("Choose an empty output directory; existing experiments are preserved")
    args.out.mkdir(parents=True, exist_ok=True)
    exclusions = json.loads(args.exclusions.read_text())
    rows, counts, failures = [], Counter(), Counter()
    for split in ("train", "valid"):
        items = gather(split, exclusions)
        for i, (path, labels) in enumerate(sorted(items.items())):
            if len(labels) != 1:
                failures[f"{split}:multiple_labels"] += 1
                continue
            label = next(iter(labels))
            crop, reason = runtime_crop(path)
            if reason:
                failures[f"{split}:{reason}"] += 1
                continue
            relative = path.relative_to(REPO).as_posix()
            name = hashlib.sha256(relative.encode()).hexdigest()[:24] + ".png"
            target = args.out / split / label / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(target), crop):
                raise RuntimeError(f"Could not write crop: {target}")
            counts[f"{split}:{label}"] += 1
            rows.append({"source": relative, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "crop": target.relative_to(args.out).as_posix(), "label": label, "split": split})
            if (i + 1) % 500 == 0:
                print(f"{split} {i + 1}/{len(items)}", flush=True)
    manifest = {"status": "experimental; no TEST processed", "counts": dict(counts),
                "failures": dict(failures), "rows": rows,
                "exclusions_sha256": hashlib.sha256(args.exclusions.read_bytes()).hexdigest(),
                "limitations": "Clinical images with simulated framing; source labels not reverified; failed localization omitted from training, but must count as misses in endpoint evaluation."}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"counts": dict(counts), "failures": dict(failures)}), flush=True)


if __name__ == "__main__":
    main()
