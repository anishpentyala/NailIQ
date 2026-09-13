"""Unified end-to-end color-track evaluation through the real Flask /analyze endpoint.

eval_color_sensitivity.py measures recall on test positives only and there was no
committed false-positive counterpart, so recall/false-positive trade-offs were being
judged from two different ad-hoc runs. This script measures, from ONE pass over ONE
split, for every CNN/heuristic color condition:

  - recall        : outside / analyzable, over images labeled with that condition
  - false-positive: outside / analyzable, over images labeled ONLY healthy
  - abstention    : inconclusive / all, on both of the above

Methodology rule this exists to enforce: anything tuned (thresholds, fusion rules,
ensemble weights) is chosen on `--split valid`; `--split test` is run once, afterwards,
to report. Split membership replicates scripts/build_color_classification_dataset.py
(KNM native split, nail-disease md5 re-split by stem, Ghana patient-grouped re-split),
so no image here was seen in training.

Every response is cached (`--cache`) with the CNN probs, heuristic verdicts and nail
bbox, so decision rules can be re-simulated offline (ml/eval/tune_color_decision.py)
without re-running the pipeline.

    backend/venv/Scripts/python.exe ml/eval/eval_end_to_end.py --split valid --cache ml/eval/e2e_valid.json
"""
import argparse
import base64
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from ml.eval.eval_color_sensitivity import (  # noqa: E402
    ARTHITAYA, ARTHITAYA_SLUGS, GHANA, KNM, KNM_SLUGS, NAIL_DISEASE, NAIL_DISEASE_SLUGS,
    SPLITS, b64, bucket_split, find_image_file, ghana_label, ghana_patient_key, load_names,
)

KNM_ALL = {**KNM_SLUGS, "Healthy Nail": "healthy"}
ND_ALL = {**NAIL_DISEASE_SLUGS, "Normal-nail": "healthy"}


def _yolo_labels(root, slugs, split, resplit):
    """{image_path: set(slugs)} for one YOLO dataset's images in `split`."""
    if not root.exists():
        return {}
    names = load_names(root)
    idx_to_slug = {i: slugs[n] for i, n in enumerate(names) if n in slugs}
    out = {}
    for src_split in (SPLITS if resplit else (split,)):
        labels_dir = root / src_split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in sorted(labels_dir.glob("*.txt")):
            if resplit and bucket_split(label_file.stem) != split:
                continue
            rows = [r.split() for r in label_file.read_text().splitlines()]
            here = {idx_to_slug[int(r[0])] for r in rows if len(r) == 5 and int(r[0]) in idx_to_slug}
            img = find_image_file(label_file) if here else None
            if img:
                out[img] = here
    return out


def gather(split):
    """{image_path: set(labels)} over every held-out source for `split`."""
    items = {}
    items.update(_yolo_labels(KNM, KNM_ALL, split, resplit=False))
    items.update(_yolo_labels(NAIL_DISEASE, ND_ALL, split, resplit=True))
    if GHANA.exists():
        for p in sorted(GHANA.glob("*.png")):
            label = ghana_label(p.name)
            if label and bucket_split(ghana_patient_key(p.name, label)) == split:
                items[p] = {label}
    # arthitaya is unlicensed for training but is still the only melanonychia source,
    # so it's used here for local evaluation only (never trained on).
    if ARTHITAYA.exists() and split == "test":
        for cls_dir in sorted(ARTHITAYA.iterdir()):
            if cls_dir.is_dir() and ARTHITAYA_SLUGS.get(cls_dir.name) == "melanonychia":
                for p in sorted(cls_dir.iterdir()):
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png") and \
                            bucket_split(f"{cls_dir.name}-{p.stem}") == split:
                        items[p] = {"melanonychia"}
    return items


def run(split):
    # eval_color_sensitivity (imported above) already pointed NAILIQ_DATABASE_URI at a
    # scratch DB before importing app -- verify, so an eval can never write real history.
    import app as app_module

    app_module._rate_limited = lambda ip: False  # test client = one IP; see CLAUDE.md
    with app_module.app.app_context():
        assert tempfile.gettempdir() in (app_module.db.engine.url.database or ""), "eval would write the real DB"
        app_module.db.create_all()
    client = app_module.app.test_client()

    side = b64(sorted((REPO / "data" / "raw" / "merged" / "test" / "healthy").glob("*.jpg"))[0])
    records = []
    items = gather(split)
    for i, (path, labels) in enumerate(sorted(items.items(), key=lambda kv: str(kv[0]))):
        top = b64(path)
        if top is None:
            continue
        resp = client.post("/analyze", json={"side_image": side, "top_image": top})
        if resp.status_code != 200:
            raise SystemExit(f"HTTP {resp.status_code} on {path} -- not a pipeline verdict, fix before trusting numbers")
        body = resp.get_json()
        findings = {}
        for f in body["findings"]:
            if f.get("track_used") not in ("color", "color_fused"):
                continue
            # Pre-validation-policy verdict: what the decision rule produced, so
            # tune_color_decision.py can replay it; `shown` is what the user sees.
            pre_policy = f.get("unvalidated_verdict")
            findings[f["label"]] = {
                "verdict": pre_policy or f["verdict"], "shown": f["verdict"],
                "failure_reason": None if pre_policy else f.get("failure_reason"),
                "heuristic": (f.get("color") or {}).get("verdict", f["verdict"]),
                "agreement": f.get("agreement"),
            }
        ml = next((f.get("ml") for f in body["findings"] if f.get("track_used") == "color_fused"), None)
        records.append({
            "path": str(path.relative_to(REPO)), "labels": sorted(labels), "findings": findings,
            "probs": (ml or {}).get("probs"), "bbox": body.get("overlay", {}).get("top_bbox_norm"),
        })
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(items)}", flush=True)
    return records


def metrics(records, verdict_of=lambda r, c: r["findings"].get(c, {}).get("verdict")):
    """{condition: {...}} recall / FP / abstention. verdict_of lets tuners re-simulate."""
    conds = sorted({c for r in records for c in r["findings"]})
    healthy = [r for r in records if r["labels"] == ["healthy"]]
    out = {}
    for c in conds:
        pos = [r for r in records if c in r["labels"]]
        row = {}
        for name, group in (("pos", pos), ("healthy", healthy)):
            v = [verdict_of(r, c) for r in group]
            outside, within = v.count("outside"), v.count("within")
            row[name] = {"n": len(group), "outside": outside, "within": within,
                         "inconclusive": len(group) - outside - within}
        p, h = row["pos"], row["healthy"]
        row["recall"] = p["outside"] / (p["outside"] + p["within"]) if p["outside"] + p["within"] else None
        row["fp_rate"] = h["outside"] / (h["outside"] + h["within"]) if h["outside"] + h["within"] else None
        tp, fp = p["outside"], h["outside"]
        # Precision at the healthy base rate of this eval set -- a relative figure only.
        row["precision_vs_healthy"] = tp / (tp + fp) if tp + fp else None
        out[c] = row
    return out


def print_metrics(m):
    print(f"\n{'condition':22s} {'recall':>14s} {'FP on healthy':>16s} {'pos abstain':>12s}")
    for c, r in m.items():
        p, h = r["pos"], r["healthy"]
        rec = f"{r['recall']:.1%} ({p['outside']}/{p['outside'] + p['within']})" if r["recall"] is not None else "n/a"
        fp = f"{r['fp_rate']:.1%} ({h['outside']}/{h['outside'] + h['within']})" if r["fp_rate"] is not None else "n/a"
        print(f"{c:22s} {rec:>14s} {fp:>16s} {p['inconclusive']:>5d}/{p['n']:<5d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["valid", "test"], required=True)
    ap.add_argument("--cache", type=Path, help="write/read per-image records JSON")
    ap.add_argument("--from-cache", action="store_true", help="only re-print metrics from --cache")
    args = ap.parse_args()

    if args.from_cache:
        records = json.loads(args.cache.read_text())
    else:
        records = run(args.split)
        if args.cache:
            args.cache.write_text(json.dumps(records))
    counts = defaultdict(int)
    for r in records:
        for label in r["labels"]:
            counts[label] += 1
    print(f"split={args.split} images={len(records)} label counts={dict(counts)}")
    print("\nDecision-rule output (before ml/infer/validation_policy.py):")
    print_metrics(metrics(records))
    print("\nWhat the user is shown (unvalidated conditions -> inconclusive):")
    print_metrics(metrics(records, lambda r, c: r["findings"].get(c, {}).get("shown", r["findings"].get(c, {}).get("verdict"))))


if __name__ == "__main__":
    main()
