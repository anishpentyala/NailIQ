"""Cache the nail crops the APP would feed a classifier, for onycholysis vs healthy.

Every full source photo goes through the same front end as production
(ml/eval/eval_onycholysis_specialist_e2e.front_end: framing sim -> quality gates -> nail_locator ->
compute_nail_region -> padded bbox crop). The crop is written to
data/raw/onych_app_crops/<split>/<onycholysis|healthy>/<source>__<stem>.png, mirroring the layout of
goal60_authorized_cls so scripts/train_onycholysis_specialist.py can train on it with --ind-root.
Photos the app would refuse (blur, glare, polish, no nail) are listed in abstained.json instead.
Splits are the same ones the colour pipeline uses. Ghana (masked patches) is skipped.

Run from repo root: ml/venv/Scripts/python.exe scripts/build_onycholysis_app_crops.py
"""
import json, shutil, sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend"))

from ml.eval.eval_end_to_end import gather                                   # noqa: E402
from ml.eval.eval_onycholysis_specialist_e2e import front_end, source_of     # noqa: E402

OUT = REPO / "data" / "raw" / "onych_app_crops"
TARGETS = ("onycholysis", "melanonychia", "leukonychia", "terrys_nails", "clubbing", "beaus_lines", "muehrckes_lines")


def _one(sp, cls, src, p, counts, abstained, i, items):
    dest = OUT / sp / cls / f"{src}__{p.stem}.png"
    if dest.exists():
        counts[(sp, cls, src)] = counts.get((sp, cls, src), 0) + 1
        return
    crop, reason = front_end(p)
    if crop is None:
        abstained.append({"split": sp, "cls": cls, "src": src, "path": str(p), "reason": reason})
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), crop)
    counts[(sp, cls, src)] = counts.get((sp, cls, src), 0) + 1
    if (i + 1) % 100 == 0:
        print(f"  {sp} {i + 1}/{len(items)}", flush=True)


def main():
    abstained, counts = [], {}
    for sp in ("train", "valid", "test"):
        items = gather(sp, include_authorized=True, include_shapes=True)
        print(sp, len(items), "source images", flush=True)
        for i, (p, labels) in enumerate(sorted(items.items(), key=lambda kv: str(kv[0]))):
            src = source_of(p)
            if src == "ghana":
                # darker-skin cohort: tiny masked patches, copied as-is (no locator), healthy only
                if labels == {"healthy"}:
                    dest = OUT / sp / "healthy" / f"ghana__{p.stem}.png"
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(p, dest)
                    counts[(sp, "healthy", "ghana")] = counts.get((sp, "healthy", "ghana"), 0) + 1
                continue
            if src == "other":
                continue
            classes = [c for c in TARGETS if c in labels] or (["healthy"] if labels == {"healthy"} else [])
            for cls in classes:
                _one(sp, cls, src, p, counts, abstained, i, items)
    json.dump(abstained, open(OUT / "abstained.json", "w"), indent=1)
    print("crops", {"/".join(k): v for k, v in sorted(counts.items())})
    ab = {}
    for a in abstained:
        k = f"{a['split']}/{a['cls']}/{a['src']}"
        ab[k] = ab.get(k, 0) + 1
    print("abstained", ab, flush=True)


if __name__ == "__main__":
    main()
