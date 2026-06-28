"""Audit the skin-tone (ITA) coverage of the image datasets.

Runs the *production* nail-region path over every image in the given dataset
roots, pulls each photo's Individual Typology Angle (`skin_ita`, computed from
the surrounding skin pixels), and bins it into the standard ITA tone bands. This
turns "we don't know which skin tones the model has seen" into an actual table.

It deliberately reuses `extract_best_contour` + `nail_region.compute_nail_region`
-- the same code `/analyze` runs -- so the numbers reflect what the model is
really exposed to (images where no finger/skin is found are reported as
`no_region`, exactly as they would be skipped at inference).

Run from the repo root:
    backend/venv/Scripts/python.exe ml/eval/audit_skin_tone.py
"""

import os
import sys
from collections import Counter, defaultdict

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml.infer.nail_region import compute_nail_region  # noqa: E402
from ml.infer.preprocessing import extract_best_contour  # noqa: E402

# Standard ITA tone bands (Fitzpatrick-aligned), light -> dark. Edges in degrees.
# Higher ITA = lighter skin. These are the canonical dermatology cut-points.
BANDS = [
    ("very_light", 55.0, 1e9),
    ("light", 41.0, 55.0),
    ("intermediate", 28.0, 41.0),
    ("tan", 10.0, 28.0),
    ("brown", -30.0, 10.0),
    ("dark", -1e9, -30.0),
]

# Dataset roots to audit: only those with whole-finger photos (skin visible).
# The color_cls crops are tight nail boxes with little/no skin, so ITA can't be
# measured there -- they're intentionally excluded.
DATASET_ROOTS = [
    "data/raw/merged/train",
    "data/raw/merged/valid",
    "data/raw/merged/test",
    "data/raw/nailcheck-3xvkl/train",
    "data/raw/nailcheck-3xvkl/valid",
    "data/raw/nailcheck-3xvkl/test",
]

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def band_for(ita):
    if ita is None:
        return "no_region"
    for name, lo, hi in BANDS:
        if lo <= ita < hi:
            return name
    return "no_region"


def ita_for_image(path):
    """Production-path ITA for one image, or None if no nail region was found."""
    image = cv2.imread(path)
    if image is None:
        return None
    contour, validation = extract_best_contour(image)
    if not validation["is_valid"]:
        return None
    region, reason = compute_nail_region(image, contour)
    if reason:
        return None
    return region.get("skin_ita")


def audit():
    overall = Counter()
    per_root = defaultdict(Counter)
    n_total = 0

    for root in DATASET_ROOTS:
        if not os.path.isdir(root):
            print(f"  (skip, missing) {root}")
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                if os.path.splitext(fn)[1].lower() not in IMG_EXTS:
                    continue
                ita = ita_for_image(os.path.join(dirpath, fn))
                band = band_for(ita)
                overall[band] += 1
                per_root[root][band] += 1
                n_total += 1
                if n_total % 200 == 0:
                    print(f"  ...{n_total} images")

    order = [b[0] for b in BANDS] + ["no_region"]
    measured = sum(overall[b] for b in order if b != "no_region")

    print("\n=== ITA tone-band coverage (all roots) ===")
    print(f"{'band':<14}{'count':>8}{'% of measured':>16}")
    for b in order:
        c = overall[b]
        pct = f"{100 * c / measured:.1f}%" if (measured and b != 'no_region') else "-"
        print(f"{b:<14}{c:>8}{pct:>16}")
    print(f"\ntotal images: {n_total}   measured (region found): {measured}   "
          f"no_region: {overall['no_region']}")

    print("\n=== per-dataset-root ===")
    for root, counts in per_root.items():
        m = sum(counts[b] for b in order if b != "no_region")
        cells = "  ".join(f"{b}:{counts[b]}" for b in order if counts[b])
        print(f"{root}  (measured {m})\n    {cells}")

    # The headline fairness signal: are the dark bands essentially empty?
    dark_like = overall["brown"] + overall["dark"]
    print("\n=== headline ===")
    if measured:
        print(f"brown+dark (ITA<10): {dark_like}  ({100 * dark_like / measured:.1f}% of measured)")
        if dark_like < 0.05 * measured:
            print("  WARNING: darker skin tones are <5% of measured data -- model is")
            print("  effectively unvalidated on dark skin. See Step 3/4 in the plan.")


if __name__ == "__main__":
    audit()
