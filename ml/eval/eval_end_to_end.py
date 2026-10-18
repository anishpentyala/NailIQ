"""Unified end-to-end color-track evaluation through the real Flask /analyze endpoint.

eval_color_sensitivity.py measures recall on test positives only and there was no
committed false-positive counterpart, so recall/false-positive trade-offs were being
judged from two different ad-hoc runs. This script measures, from ONE pass over ONE
split, for every CNN/heuristic color condition:

  - recall        : outside / ALL positives, including inconclusive results as misses
  - false-positive: outside / ALL images labeled ONLY healthy
  - abstention    : inconclusive / all, on both of the above

Methodology rule this exists to enforce: anything tuned (thresholds, fusion rules,
ensemble weights) is chosen on `--split valid`; `--split test` is run once, afterwards,
to report. Split membership replicates scripts/build_color_classification_dataset.py
(KNM native split, chaa md5 re-split by stem, Ghana patient-grouped re-split),
so no image here was seen in training.

Every response is cached (`--cache`) with the CNN probs, heuristic verdicts and nail
bbox, so decision rules can be re-simulated offline (ml/eval/tune_color_decision.py)
without re-running the pipeline.

    backend/venv/Scripts/python.exe ml/eval/eval_end_to_end.py --split valid --cache ml/eval/e2e_valid.json
"""
import argparse
import base64
import hashlib
import json
import math
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

import cv2

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from ml.eval.eval_color_sensitivity import (  # noqa: E402
    ANEMIA, ARTHITAYA, ARTHITAYA_SLUGS, CHAA, CHAA_SLUGS, GHANA, KNM, KNM_SLUGS, NIHATI,
    SPLITS, anemia_source_key, b64, bucket_split, find_image_file, ghana_label,
    ghana_patient_key, load_names,
)

KNM_ALL = {**KNM_SLUGS, "Healthy Nail": "healthy"}
CHAA_ALL = {**CHAA_SLUGS, "Healthy": "healthy"}


def evaluation_fingerprint(model_dir=None, locator_dir=None, routing_manifest=None):
    """Bind cached results to the weights and code that actually produced them."""
    paths = list((REPO / "ml" / "infer").glob("*.py"))
    model_dirs = {REPO / "ml" / "models"}
    if model_dir:
        model_dirs.add(model_dir)
    if locator_dir:
        model_dirs.add(locator_dir)
    for directory in model_dirs:
        paths += list(directory.glob("*.pt")) + list(directory.glob("*.json"))
    paths += [Path(__file__), REPO / "ml/eval/eval_color_sensitivity.py",
              REPO / "backend/app.py", REPO / "scripts/build_color_classification_dataset.py",
              REPO / 'ml/nail_detection_model.py', REPO / 'scripts/prepare_color_exclusions.py']
    paths += [p for p in (REPO / 'ml/eval/withholding_checks.py', REPO / 'ml/eval/confirmation_cohort.py',
              REPO / 'scripts/select_goal60_withholding.py', REPO / 'scripts/check_goal60_withholding.py',
              REPO / 'scripts/evaluate_goal60_confirmation.py') if p.is_file()]
    result = {}
    for path in sorted(set(paths)):
        with path.open("rb") as source:
            result[str(path)] = hashlib.file_digest(source, "sha256").hexdigest()
    routing_manifest = routing_manifest or os.environ.get('NAILIQ_ROUTING_MANIFEST')
    if routing_manifest:
        from ml.infer.routing import configured_runtime, RoutingRuntime
        runtime = (configured_runtime() if str(Path(routing_manifest).resolve()) == os.environ.get('NAILIQ_ROUTING_MANIFEST')
                   else RoutingRuntime(routing_manifest))
        # Rehash current files, rather than trusting the runtime's initialization hashes.
        for name in runtime.dependencies:
            with Path(name).open('rb') as source:
                result[name] = hashlib.file_digest(source, 'sha256').hexdigest()
        for path in (REPO / 'scripts/run_goal60_round2.py', REPO / 'ml/eval/routed_replay.py'):
            if path.is_file():
                result[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _yolo_labels(root, slugs, split, resplit):
    """{image_path: set(slugs)} for one YOLO dataset's images in `split`. Handles both
    fixed 5-field detection rows (KNM) and variable-length segmentation polygon rows
    (chaa: class + >=3 x/y point pairs) -- see scripts/build_color_classification_
    dataset.py's _row_bbox for the training-side counterpart of this `>= 5` filter.
    """
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
            here = {idx_to_slug[int(r[0])] for r in rows if len(r) >= 5 and int(r[0]) in idx_to_slug}
            img = find_image_file(label_file) if here else None
            if img:
                out[img] = here
    return out


def gather(split, exclusions=None, include_authorized=False, include_shapes=False):
    """{image_path: set(labels)} over every held-out source for `split`."""
    items = {}
    knm_labels = {**KNM_ALL, **({'Clubbing': 'clubbing', 'Koilonychia': 'koilonychia'} if include_shapes else {})}
    chaa_labels = {**CHAA_ALL, **({'Spoon Nail': 'koilonychia'} if include_shapes else {})}
    items.update(_yolo_labels(KNM, knm_labels, split, resplit=False))
    items.update(_yolo_labels(CHAA, chaa_labels, split, resplit=True))
    if include_authorized:
        from scripts.build_color_classification_dataset import arthitaya_samples
        for path, label, _, _ in arthitaya_samples(split):
            if label != 'mees_lines' and (include_shapes or label not in {'clubbing', 'koilonychia'}):
                items[path] = {label}
    if GHANA.exists():
        for p in sorted(GHANA.glob("*.png")):
            label = ghana_label(p.name)
            if label and bucket_split(ghana_patient_key(p.name, label)) == split:
                items[p] = {label}
    # arthitaya is unlicensed for training but is still the only melanonychia source,
    # so it's used here for local evaluation only (never trained on).
    if not include_authorized and ARTHITAYA.exists() and split == "test":
        for cls_dir in sorted(ARTHITAYA.iterdir()):
            if cls_dir.is_dir() and ARTHITAYA_SLUGS.get(cls_dir.name) == "melanonychia":
                for p in sorted(cls_dir.iterdir()):
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png") and \
                            bucket_split(f"{cls_dir.name}-{p.stem}") == split:
                        items[p] = {"melanonychia"}
    # NIHATI: folder name is already the slug (see eval_color_sensitivity.gather_positives'
    # comment); re-split by image id, same as training.
    if NIHATI.exists():
        for src_split_dir in NIHATI.iterdir():
            if not src_split_dir.is_dir():
                continue
            for slug_dir in src_split_dir.iterdir():
                if not slug_dir.is_dir():
                    continue
                for p in slug_dir.iterdir():
                    if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                        continue
                    image_id = p.stem.split("_", 1)[0]
                    if bucket_split(image_id) == split:
                        items.setdefault(p, set()).add(slug_dir.name)
    # anemia: only `anemic_nail` (class 0) -> pallor, re-split by source-photo key.
    if ANEMIA.exists():
        for src_split in SPLITS:
            labels_dir = ANEMIA / src_split / "labels"
            if not labels_dir.exists():
                continue
            for label_file in sorted(labels_dir.glob("*.txt")):
                has_anemic = any(p.split()[0] == "0" for p in label_file.read_text().splitlines()
                                  if len(p.split()) == 5)
                if not has_anemic or bucket_split(anemia_source_key(label_file.stem)) != split:
                    continue
                img = find_image_file(label_file)
                if img:
                    items.setdefault(img, set()).add("pallor")
    if exclusions:
        from scripts.prepare_color_exclusions import excludes_source
        items = {p: labels for p, labels in items.items() if not excludes_source(p, exclusions)}
    return items


def run(split, exclusions=None, include_authorized=False, include_shapes=False, roi_mode='auto'):
    # A separate database per process keeps evaluation away from real scan history.
    from ml.eval.eval_color_sensitivity import create_eval_client
    app_module, client = create_eval_client()

    app_module._rate_limited = lambda ip: False  # test client = one IP; see CLAUDE.md
    with app_module.app.app_context():
        # normalize separators -- the URI is built with forward slashes (see
        # eval_color_sensitivity.py) but tempfile.gettempdir() returns OS-native ones,
        # so a raw substring check false-negatives on Windows even when the DB is
        # correctly scratch-scoped.
        db_path = (app_module.db.engine.url.database or "").replace("\\", "/")
        assert tempfile.gettempdir().replace("\\", "/") in db_path, "eval would write the real DB"
        app_module.db.create_all()
    client = app_module.app.test_client()

    # This benchmark has no paired side ground truth. A synthetic unreadable side
    # isolates appearance and never borrows a TEST image during VALID selection.
    import numpy as np
    _, buffer = cv2.imencode('.jpg', np.full((64, 64, 3), 128, dtype=np.uint8))
    side = base64.b64encode(buffer).decode()
    records = []
    print(f'Gathering {split} source images...', flush=True)
    items = gather(split, exclusions, include_authorized, include_shapes)
    print(f'Endpoint scoring {len(items)} source images.', flush=True)
    for i, (path, labels) in enumerate(sorted(items.items(), key=lambda kv: str(kv[0]))):
        top = b64(path)
        if top is None:
            raise RuntimeError(f"Unreadable evaluation image: {path}; refusing to silently change the denominator")
        payload = {'side_image': side, 'top_image': top}
        if roi_mode == 'annotation':
            box = annotation_bbox(path)
            if box is not None:
                payload['top_nail_bbox'] = box
        resp = client.post('/analyze', json=payload)
        if resp.status_code != 200:
            raise SystemExit(f"HTTP {resp.status_code} on {path} -- not a pipeline verdict, fix before trusting numbers")
        body = resp.get_json()
        findings = {}
        for f in body["findings"]:
            if f.get("track_used") not in ("color", "color_fused", 'appearance') and not body.get('overlay', {}).get('routing_digest'):
                continue
            # Pre-validation-policy verdict: what the decision rule produced, so
            # tune_color_decision.py can replay it; `shown` is what the user sees.
            pre_policy = f.get("unvalidated_verdict")
            findings[f["label"]] = {
                "verdict": pre_policy or f["verdict"], "shown": f["verdict"],
                "failure_reason": None if pre_policy else f.get("failure_reason"),
                "heuristic": (f.get("color") or {}).get("verdict", f["verdict"]),
                "agreement": f.get("agreement"),
                'evidence_type': f.get('evidence_type'),
                'roi_only': f.get('roi_only', False),
                **({'route_id': f.get('route_id'), 'model_id': f.get('model_id'), 'bbox_norm': f.get('bbox_norm')}
                   if body.get('overlay', {}).get('routing_digest') else {}),
            }
        ml = next((f.get("ml") for f in body["findings"]
                   if f.get("ml") and f.get("track_used") in {'color_fused', 'appearance'}), None)
        records.append({
            "path": str(path.relative_to(REPO)), "labels": sorted(labels), "findings": findings,
            "probs": (ml or {}).get("probs"), "bbox": body.get("overlay", {}).get("top_bbox_norm"),
            'roi_mode': body.get('overlay', {}).get('roi_mode'),
            'oracle_box_available': 'top_nail_bbox' in payload,
            'appearance_eligible': {f['label']: f.get('geometry', f).get('verdict') == 'inconclusive'
                                    for f in body['findings'] if f['label'] in {'clubbing', 'koilonychia'}},
            **({'cache_version': 2, 'branches': body['overlay']['routing_evidence'],
                'geometry_evidence': body['overlay'].get('geometry_evidence', {}),
                'routing_digest': body['overlay']['routing_digest']} if body.get('overlay', {}).get('routing_digest') else {}),
        })
        if i < 3 or (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(items)}", flush=True)
    return records


def wilson_interval(successes, total):
    if not total:
        return None
    z, p = 1.959963984540054, successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - margin), min(1, center + margin)]


def annotation_bbox(path):
    """Oracle diagnostic only: largest annotation, selected without its condition label."""
    from scripts.build_color_classification_dataset import _row_bbox
    label_file = path.parent.parent / 'labels' / (path.stem + '.txt')
    if not label_file.is_file():
        return None
    boxes = [_row_bbox(list(map(float, row.split()[1:]))) for row in label_file.read_text().splitlines()
             if len(row.split()) >= 5]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    cx, cy, bw, bh = max(boxes, key=lambda box: box[2] * box[3])
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f'Unreadable annotation image: {path}')
    h, w = image.shape[:2]
    scale = max(1.0, 480 / max(h, w))
    h, w = round(h * scale), round(w * scale)
    pad = int(0.3 * max(h, w))
    return [(max(0, cx - bw / 2) * w + pad) / (w + 2 * pad),
            (max(0, cy - bh / 2) * h + pad) / (h + 2 * pad),
            (min(1, cx + bw / 2) * w + pad) / (w + 2 * pad),
            (min(1, cy + bh / 2) * h + pad) / (h + 2 * pad)]


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
        row["recall"] = p["outside"] / p["n"] if p["n"] else None
        row["fp_rate"] = h["outside"] / h["n"] if h["n"] else None
        row['recall_ci95'] = wilson_interval(p['outside'], p['n'])
        row['fp_ci95'] = wilson_interval(h['outside'], h['n'])
        row["healthy_correct_rate"] = h["within"] / h["n"] if h["n"] else None
        row["balanced_accuracy"] = (row["recall"] + row["healthy_correct_rate"]) / 2 if p["n"] and h["n"] else None
        tp, fp = p["outside"], h["outside"]
        # Precision at the healthy base rate of this eval set -- a relative figure only.
        row["precision_vs_healthy"] = tp / (tp + fp) if tp + fp else None
        out[c] = row
    return out


def print_metrics(m):
    print(f"\n{'condition':22s} {'recall':>14s} {'FP on healthy':>16s} {'pos abstain':>12s}")
    for c, r in m.items():
        p, h = r["pos"], r["healthy"]
        rec = f"{r['recall']:.1%} ({p['outside']}/{p['n']})" if r["recall"] is not None else "n/a"
        fp = f"{r['fp_rate']:.1%} ({h['outside']}/{h['n']})" if r["fp_rate"] is not None else "n/a"
        print(f"{c:22s} {rec:>14s} {fp:>16s} {p['inconclusive']:>5d}/{p['n']:<5d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["valid", "test"], required=True)
    ap.add_argument("--cache", type=Path, help="write/read per-image records JSON")
    ap.add_argument("--from-cache", action="store_true", help="only re-print metrics from --cache")
    ap.add_argument("--exclusions", type=Path)
    ap.add_argument("--model-dir", type=Path, help="Evaluate isolated color-model candidates without replacing shipped weights")
    ap.add_argument('--locator-dir', type=Path)
    ap.add_argument('--routing-manifest', type=Path)
    ap.add_argument('--include-authorized', action='store_true')
    ap.add_argument('--include-shapes', action='store_true', help='Evaluate top-photo appearance; never side geometry')
    ap.add_argument('--roi-mode', choices=['auto', 'annotation'], default='auto')
    args = ap.parse_args()
    if args.routing_manifest:
        if args.split != 'valid':
            ap.error('Round-two routing may use VALID only; historical TEST is not fresh confirmation')
        os.environ['NAILIQ_ROUTING_MANIFEST'] = str(args.routing_manifest.resolve())
        import torch
        torch.set_num_threads(2)
    if args.locator_dir:
        from ml.infer import nail_locator
        nail_locator._MODELS = args.locator_dir.resolve()
    if args.model_dir:
        from ml.infer import color_classifier
        args.model_dir = args.model_dir.resolve()
        color_classifier._MODELS = args.model_dir
        color_classifier._LABELS_PATH = args.model_dir / "nail_color_classifier_labels.json"
        if not color_classifier._LABELS_PATH.is_file():
            raise SystemExit("Candidate model manifest is missing")

    if args.from_cache:
        records = json.loads(args.cache.read_text())
        meta_path = args.cache.with_suffix(".meta.json")
        if not meta_path.exists():
            print("WARNING: legacy cache has no fingerprint; current-model parity is unverified.")
        else:
            metadata = json.loads(meta_path.read_text())
            if metadata["fingerprint"] != evaluation_fingerprint(args.model_dir, args.locator_dir):
                print("WARNING: code or weights changed; this is a historical cache, not current performance.")
        if args.exclusions:
            from scripts.prepare_color_exclusions import excludes_source
            exclusions = json.loads(args.exclusions.read_text())
            records = [r for r in records if not excludes_source(REPO / r["path"], exclusions)]
    else:
        def input_identity():
            current = gather(args.split, exclusions, args.include_authorized, args.include_shapes)
            return [(str(path.relative_to(REPO)), sorted(labels), hashlib.sha256(path.read_bytes()).hexdigest())
                    for path, labels in sorted(current.items(), key=lambda item: str(item[0]))]
        print('Fingerprinting model and decision files...', flush=True)
        fingerprint = evaluation_fingerprint(args.model_dir, args.locator_dir)
        exclusions = json.loads(args.exclusions.read_text()) if args.exclusions else None
        exclusion_digest = hashlib.sha256(args.exclusions.read_bytes()).hexdigest() if args.exclusions else None
        identity = input_identity() if args.routing_manifest else None
        records = run(args.split, exclusions, args.include_authorized, args.include_shapes, args.roi_mode)
        if fingerprint != evaluation_fingerprint(args.model_dir, args.locator_dir):
            raise RuntimeError("Code or weights changed during evaluation; rerun before trusting results")
        if args.routing_manifest and (identity != input_identity() or
                exclusion_digest != (hashlib.sha256(args.exclusions.read_bytes()).hexdigest() if args.exclusions else None)):
            raise RuntimeError('Inputs, labels, or exclusions changed during evaluation')
        if args.cache:
            args.cache.write_text(json.dumps(records))
            args.cache.with_suffix(".meta.json").write_text(json.dumps({
                "split": args.split, "created_at": datetime.now(timezone.utc).isoformat(),
                "fingerprint": fingerprint, "images": len(records),
                "scope": 'clinical images with simulated framing; side geometry excluded; ' +
                         ('annotation boxes are oracle diagnostics, not user/automatic accuracy' if args.roi_mode == 'annotation' else 'automatic localization'),
                'include_authorized': args.include_authorized, 'include_shapes': args.include_shapes,
                'roi_mode': args.roi_mode,
                **({'cache_version': 2, 'routing_manifest': str(args.routing_manifest.resolve()),
                    'routing_sha256': hashlib.sha256(args.routing_manifest.read_bytes()).hexdigest(),
                    'execution_environment': {'torch': str(torch.__version__), 'cuda': torch.version.cuda,
                        'cudnn': torch.backends.cudnn.version(),
                        'device': json.loads(args.routing_manifest.read_text()).get('device', 'cpu'),
                        'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                        'tf32': False, 'python': sys.version},
                    'input_label_manifest_sha256': hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()}
                   if args.routing_manifest else {}),
                "dataset_leakage_audited": False,
                "exclusions_sha256": hashlib.sha256(args.exclusions.read_bytes()).hexdigest() if args.exclusions else None,
            }, indent=2))
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
