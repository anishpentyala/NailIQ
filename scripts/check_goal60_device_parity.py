"""Exact CPU/GPU endpoint verdict and route regression on 64 development frames."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_color_sensitivity import b64, create_eval_client
from ml.eval.eval_end_to_end import evaluation_fingerprint, gather
from ml.infer.routing import digest, rules_for
from scripts.report_goal60 import CONDITIONS


def sample(records, spec, metadata, size=64):
    chosen = {}
    stable = lambda r: hashlib.sha256(r['path'].encode()).hexdigest()
    def add(rows, count):
        for row in list(rows)[:count]:
            chosen[row['path']] = row
    for condition in CONDITIONS:
        add(sorted((r for r in records if condition in r['labels']), key=stable), 2)
    add(sorted((r for r in records if r['labels'] == ['healthy']), key=stable), 8)
    add(sorted((r for r in records if any(b.get('failure') for b in r['branches'].values())), key=stable), 8)
    margins = []
    for r in records:
        distances = []
        for c, config in spec['conditions'].items():
            rule = rules_for(metadata[config['model']], c, config.get('rules'))
            thresholds = [rule['floors'].get(c, .45), rule['ovr'].get(c),
                          rule['appearance'].get('floor'), rule['appearance'].get('healthy_floor')]
            for branch in r['branches'].values():
                probabilities = branch['models'].get(config['model'], {}).get('probs') or {}
                if c in probabilities:
                    distances.extend(abs(probabilities[c]-v) for v in thresholds if v is not None)
                    distances.append(abs(probabilities.get('healthy', 0)-rule['appearance'].get('healthy_floor', .45)))
        margins.append((min(distances, default=2), stable(r), r))
    for _, _, row in sorted(margins, key=lambda t: t[:2]):
        if len(chosen) >= size:
            break
        chosen[row['path']] = row
    return sorted(chosen.values(), key=lambda r: r['path'])


def cpu_spec(spec, parent):
    result = {**spec, 'device': 'cpu',
              'models': {key: str((parent / path).resolve()) for key, path in spec['models'].items()}}
    for key in ('locator', 'validation_evidence'):
        if spec.get(key):
            result[key] = str((parent / spec[key]).resolve())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.cache.read_text())
    meta = json.loads(args.cache.with_suffix('.meta.json').read_text())
    if meta.get('split') != 'valid' or meta.get('routing_sha256') != digest(args.manifest):
        raise ValueError('Matching VALID GPU cache required')
    for path, expected in meta['fingerprint'].items():
        if digest(REPO / path) != expected:
            raise ValueError('Stale GPU dependency evidence')
    exclusion_path = REPO / 'data/raw/goal60_exclusions_v3.json'
    exclusions = json.loads(exclusion_path.read_text())
    current = gather('valid', exclusions, meta['include_authorized'], meta['include_shapes'])
    identity = [(str(p.relative_to(REPO)), sorted(labels), digest(p))
                for p, labels in sorted(current.items(), key=lambda item: str(item[0]))]
    if (meta['exclusions_sha256'] != digest(exclusion_path) or
            meta['input_label_manifest_sha256'] != hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()):
        raise ValueError('Stale GPU input or label evidence')
    spec = json.loads(args.manifest.read_text())
    metadata = {key: json.loads((args.manifest.parent/path/'nail_color_classifier_labels.json').read_text())
                for key, path in spec['models'].items()}
    selected = sample(records, spec, metadata)
    cpu = cpu_spec(spec, args.manifest.parent)
    cpu_path = args.out.with_suffix('.cpu_manifest.json')
    cpu_path.write_text(json.dumps(cpu, indent=2))
    os.environ['NAILIQ_ROUTING_MANIFEST'] = str(cpu_path.resolve())
    import torch
    torch.set_num_threads(2)
    fingerprint = evaluation_fingerprint()
    _, client = create_eval_client()
    _, buffer = cv2.imencode('.jpg', np.full((64, 64, 3), 128, dtype=np.uint8))
    side = base64.b64encode(buffer).decode()
    differences, evidence = [], []
    max_probability_delta, max_bbox_delta = 0., 0.
    for i, row in enumerate(selected):
        response = client.post('/analyze', json={'side_image': side, 'top_image': b64(REPO/row['path'])})
        if response.status_code != 200:
            raise ValueError('CPU endpoint failure')
        body = response.get_json()
        findings = {f['label']: f for f in body['findings']}
        for c in CONDITIONS:
            actual, expected = findings[c], row['findings'][c]
            before = actual.get('unvalidated_verdict', actual['verdict'])
            if (before, actual['verdict'], actual.get('route_id')) != (expected['verdict'], expected['shown'], expected.get('route_id')):
                differences.append({'path': row['path'], 'condition': c,
                    'cpu': [before, actual['verdict'], actual.get('route_id')],
                    'gpu': [expected['verdict'], expected['shown'], expected.get('route_id')]})
            if actual.get('agreement') != expected.get('agreement'):
                differences.append({'path': row['path'], 'condition': c, 'type': 'agreement'})
        for key, branch in body['overlay']['routing_evidence'].items():
            other = row['branches'][key]
            if branch.get('bbox') and other.get('bbox'):
                max_bbox_delta = max(max_bbox_delta, max(abs(a-b) for a,b in zip(branch['bbox'],other['bbox'])))
            for model, value in branch['models'].items():
                a, b = value.get('probs') or {}, other['models'].get(model, {}).get('probs') or {}
                if set(a) == set(b) and a:
                    max_probability_delta = max(max_probability_delta, max(abs(a[c]-b[c]) for c in a))
        evidence.append({'path': row['path'], 'labels': row['labels'], 'image_sha256': digest(REPO/row['path'])})
        print(f'{i+1}/{len(selected)} CPU parity frames', flush=True)
    if evaluation_fingerprint() != fingerprint:
        raise ValueError('CPU dependencies changed during parity')
    original_hashes = {path: sha for path, _, sha in identity}
    if any(item['image_sha256'] != original_hashes[item['path']] for item in evidence):
        raise ValueError('Parity input images changed during scoring')
    result = {'scope': 'bounded device regression, not population or clinical confirmation',
              'images': len(selected), 'findings_checked': len(selected)*len(CONDITIONS),
              'mismatches': len(differences), 'differences': differences, 'evidence': evidence,
              'maximum_rounded_probability_delta': max_probability_delta,
              'maximum_normalized_bbox_delta': max_bbox_delta, 'cpu_fingerprint': fingerprint,
              'gpu_cache_sha256': digest(args.cache), 'manifest_sha256': digest(args.manifest),
              'harness_sha256': digest(__file__)}
    from ml.infer.routing import RoutingRuntime
    result['bundle_sha256'] = RoutingRuntime(cpu_path).bundle_sha256
    args.out.write_text(json.dumps(result, indent=2))
    if differences:
        raise ValueError(f'CPU/GPU verdict or route mismatches: {len(differences)}')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','cpu_fingerprint','differences')}), flush=True)


if __name__ == '__main__':
    main()
