"""Regression check on the existing healthy phone subject; not a population benchmark."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_color_sensitivity import create_eval_client
from ml.eval.eval_end_to_end import evaluation_fingerprint
from ml.infer import color_classifier, nail_locator

GUIDE = {'side': (220, 320, 480, 750), 'top': (280, 420, 500, 750)}
# Selected by visual review of the known healthy image, before candidate scoring.
HEALTHY_TOP_BOX = [0.43, 0.42, 0.59, 0.55]


def encoded(image):
    ok, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError('JPEG encoding failed')
    return base64.b64encode(buffer).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path)
    parser.add_argument('--routing-manifest', type=Path)
    parser.add_argument('--locator-dir', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.model_dir and not args.routing_manifest:
        parser.error('Specify --model-dir or --routing-manifest')
    if args.routing_manifest:
        os.environ['NAILIQ_ROUTING_MANIFEST'] = str(args.routing_manifest.resolve())
        import torch
        torch.set_num_threads(2)
    args.model_dir = args.model_dir.resolve() if args.model_dir else None
    if args.locator_dir:
        args.locator_dir = args.locator_dir.resolve()
    fingerprint = evaluation_fingerprint(args.model_dir, args.locator_dir)
    if args.model_dir:
        color_classifier._MODELS = args.model_dir
        color_classifier._LABELS_PATH = color_classifier._MODELS / 'nail_color_classifier_labels.json'
    if args.locator_dir:
        nail_locator._MODELS = args.locator_dir.resolve()
    app_module, client = create_eval_client()
    app_module._rate_limited = lambda _: False
    root = REPO / 'data/real_eval/healthy'
    images = {view: cv2.imread(str(root / f'anish1_{view}.jpg')) for view in GUIDE}
    source_hashes = {view: hashlib.sha256((root / f'anish1_{view}.jpg').read_bytes()).hexdigest() for view in GUIDE}
    if any(image is None for image in images.values()):
        raise RuntimeError('Healthy bootstrap subject photos are missing')
    rows = []
    for mode in ('raw', 'guide', 'raw_assisted', 'guide_assisted'):
        submitted = {}
        for view, image in images.items():
            if mode.startswith('guide'):
                x0, y0, x1, y1 = GUIDE[view]
                image = image[y0:y1, x0:x1]
            submitted[view + '_image'] = encoded(image)
        if mode.endswith('assisted'):
            box = list(HEALTHY_TOP_BOX)
            if mode.startswith('guide'):
                h, w = images['top'].shape[:2]
                x0, y0, x1, y1 = GUIDE['top']
                box = [(box[0] * w - x0) / (x1 - x0), (box[1] * h - y0) / (y1 - y0),
                       (box[2] * w - x0) / (x1 - x0), (box[3] * h - y0) / (y1 - y0)]
            submitted['top_nail_bbox'] = box
        response = client.post('/analyze', json=submitted)
        if response.status_code != 200:
            raise RuntimeError(f'Endpoint failed: HTTP {response.status_code}')
        findings = response.get_json()['findings']
        rows.append({'mode': mode, 'findings': findings,
                     'shown_false_positives': [f['label'] for f in findings if f['verdict'] == 'outside'],
                     'pre_policy_false_positives': [f['label'] for f in findings
                         if f.get('unvalidated_verdict', f['verdict']) == 'outside']})
    shown_pass = all(not row['shown_false_positives'] for row in rows)
    raw_pass = all(not row['pre_policy_false_positives'] for row in rows)
    if fingerprint != evaluation_fingerprint(args.model_dir, args.locator_dir):
        raise RuntimeError('Inference code or candidate weights changed during the phone check')
    if source_hashes != {view: hashlib.sha256((root / f'anish1_{view}.jpg').read_bytes()).hexdigest() for view in GUIDE}:
        raise RuntimeError('Phone photos changed during the check')
    result = {'subject_count': 1, 'scope': 'existing healthy bootstrap regression only; assisted boxes selected by reviewer, not a user study',
              'reviewed_raw_top_box': HEALTHY_TOP_BOX, 'rows': rows,
              'fingerprint': fingerprint, 'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_hashes': source_hashes, 'routing_manifest': str(args.routing_manifest) if args.routing_manifest else None,
              'passes_shown': shown_pass, 'passes_pre_policy': raw_pass, 'passes': shown_pass and raw_pass}
    if args.routing_manifest:
        from ml.infer.routing import RoutingRuntime
        result['bundle_sha256'] = RoutingRuntime(args.routing_manifest).bundle_sha256
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key not in {'rows', 'fingerprint', 'source_hashes', 'harness_sha256'}}), flush=True)
    print(json.dumps([{k: v for k, v in row.items() if k != 'findings'} for row in rows]), flush=True)


if __name__ == '__main__':
    main()
