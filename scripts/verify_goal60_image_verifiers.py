"""Check frozen research verifier parity, endpoint crops and one retained phone subject."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.eval_color_sensitivity import b64, create_eval_client
from ml.eval.image_verifier import raw_stage, shadow, verifier_score
from ml.infer.color_classifier import _crop_to_bbox
from ml.infer.preprocessing import decode_base64_image, extract_best_contour
from ml.infer import nail_region
from ml.infer.routing import RoutingRuntime
from ml.infer.validation_evidence import file_hash
from scripts.evaluate_goal60_image_verifiers import REFERENCE, check_lock, load_models
from scripts.evaluate_goal60_phone import GUIDE, HEALTHY_TOP_BOX, encoded
from scripts.build_runtime_color_crops import runtime_crop
from scripts.build_goal60_reviewed_specialist import reviewed_crop


def verify(out):
    destination = out / 'verification.json'
    if destination.exists():
        raise ValueError('Preserve previous verification')
    lock, records = check_lock(out)
    cpu = load_models(out, 'cpu')
    gpu = load_models(out, 'cuda:0')
    os.environ['NAILIQ_ROUTING_MANIFEST'] = str(REFERENCE.resolve())
    _, client = create_eval_client()
    runtime = RoutingRuntime(REFERENCE)
    metadata = {k: m.metadata for k, m in runtime.models.items()}
    _, buffer = cv2.imencode('.jpg', np.full((64, 64, 3), 128, np.uint8))
    side = base64.b64encode(buffer).decode()
    selected = []
    for condition in ('terrys_nails', 'pallor', 'healthy'):
        selected.extend([r for r in records if condition in r['labels']][:12])
    endpoint_mismatches, crop_mismatches, device_mismatches = [], [], []
    retained_crop_checks, retained_crop_mismatches = 0, []
    for c in cpu:
        manifest = json.loads((out / c / 'manifest.json').read_text())
        for split in ('train', 'valid'):
            for row in [r for r in manifest['rows'] if r['split'] == split][:8]:
                crop, reason = (reviewed_crop(Path(row['image_path'])) if 'image_path' in row
                                else runtime_crop(ROOT / row['path']))
                retained = cv2.imread(str(out / c / row['crop']))
                retained_crop_checks += 1
                if reason or retained is None or not np.array_equal(crop, retained):
                    retained_crop_mismatches.append(row['path'])
    max_difference = 0.
    for i, record in enumerate(selected):
        top = b64(ROOT / record['path'].replace('\\', '/'))
        response = client.post('/analyze', json={'side_image': side, 'top_image': top})
        if response.status_code != 200:
            raise RuntimeError('Endpoint parity request failed')
        body = response.get_json()
        findings = {f['label']: f for f in body['findings']}
        branches = body['overlay']['routing_evidence']
        for c, f in record['findings'].items():
            if f['shown'] != findings[c]['verdict'] or f['verdict'] != findings[c].get('unvalidated_verdict', findings[c]['verdict']):
                endpoint_mismatches.append([record['path'], c])
        image = decode_base64_image(top)
        branch = branches['legacy']
        if not branch['failure'] and branch['bbox']:
            contour, validation = extract_best_contour(image)
            region, reason = nail_region.compute_nail_region(image, contour) if validation['is_valid'] else (None, validation['reason'])
            if reason or not np.array_equal(_crop_to_bbox(image, region['bbox_norm']), _crop_to_bbox(image, branch['bbox'])):
                crop_mismatches.append(record['path'])
        for c in cpu:
            a, reason_a = verifier_score(top, branches, cpu[c], c)
            b, reason_b = verifier_score(top, branches, gpu[c], c)
            stage = raw_stage({'cache_version': 2, 'branches': branches}, metadata, c)
            if a is not None and b is not None:
                max_difference = max(max_difference, abs(a - b))
            if reason_a != reason_b or shadow(findings[c]['verdict'], stage, a, lock['thresholds'][c]) != shadow(findings[c]['verdict'], stage, b, lock['thresholds'][c]):
                device_mismatches.append([record['path'], c])
        if i % 12 == 0:
            print(f'Endpoint/crop/device verification {i+1}/{len(selected)}', flush=True)
    root = ROOT / 'data/real_eval/healthy'
    paths = {view: root / f'anish1_{view}.jpg' for view in GUIDE}
    images = {view: cv2.imread(str(path)) for view, path in paths.items()}
    if any(image is None for image in images.values()):
        raise ValueError('Retained phone subject missing; do not report phone pass')
    hashes = {view: file_hash(path) for view, path in paths.items()}
    phone = []
    for mode in ('raw', 'guide', 'raw_assisted', 'guide_assisted'):
        payload = {}
        for view, image in images.items():
            if mode.startswith('guide'):
                x0, y0, x1, y1 = GUIDE[view]
                image = image[y0:y1, x0:x1]
            payload[view + '_image'] = encoded(image)
        if mode.endswith('assisted'):
            box = list(HEALTHY_TOP_BOX)
            if mode.startswith('guide'):
                h, w = images['top'].shape[:2]
                x0, y0, x1, y1 = GUIDE['top']
                box = [(box[0]*w-x0)/(x1-x0), (box[1]*h-y0)/(y1-y0),
                       (box[2]*w-x0)/(x1-x0), (box[3]*h-y0)/(y1-y0)]
            payload['top_nail_bbox'] = box
        response = client.post('/analyze', json=payload)
        if response.status_code != 200:
            raise RuntimeError('Phone regression request failed')
        body = response.get_json()
        branches = body['overlay']['routing_evidence']
        actual = {f['label']: f['verdict'] for f in body['findings']}
        hypothetical = dict(actual)
        predictions = {}
        for c in gpu:
            probability, reason = verifier_score(payload['top_image'], branches, gpu[c], c)
            # Assisted crops were not in verifier training; preserve reference.
            stage = raw_stage({'cache_version': 2, 'branches': branches}, metadata, c)
            result = shadow(actual[c], stage, probability, lock['thresholds'][c])
            hypothetical[c] = result['hypothetical_shown']
            predictions[c] = {'stage1': stage, 'probability': probability, 'failure': reason}
        phone.append({'mode': mode, 'actual_flags': [c for c, v in actual.items() if v == 'outside'],
            'hypothetical_flags': [c for c, v in hypothetical.items() if v == 'outside'], 'verifiers': predictions})
    stresses = []
    original = images['top']
    mutations = {'dark': (original.astype(float)*.12).astype(np.uint8),
        'glare': np.full_like(original, 255), 'blur': cv2.GaussianBlur(original, (81, 81), 0),
        'blank': np.full_like(original, 128)}
    for name, image in mutations.items():
        top = encoded(image)
        branches, _ = runtime.evidence(top)
        for c in gpu:
            probability, reason = verifier_score(top, branches, gpu[c], c)
            stage = raw_stage({'cache_version': 2, 'branches': branches}, metadata, c)
            result = shadow('inconclusive', stage, probability, lock['thresholds'][c])
            stresses.append({'mutation': name, 'condition': c, 'stage1': stage, 'probability': probability,
                'failure': reason, 'hypothetical_positive': result['added_positive']})
    for c in gpu:
        invalid_photo = base64.b64encode(b'valid base64, but not an image file').decode()
        probability, reason = verifier_score(invalid_photo, {'legacy': {'bbox': [0, 0, 1, 1]}}, gpu[c], c)
        stresses.append({'mutation': 'invalid_image', 'condition': c, 'probability': probability,
            'failure': reason, 'hypothetical_positive': shadow('inconclusive', 'outside', probability, lock['thresholds'][c])['added_positive']})
    malformed = client.post('/analyze', json={'side_image': side, 'top_image': 'not an image'})
    malformed_rejected = malformed.status_code == 400
    if hashes != {view: file_hash(path) for view, path in paths.items()}:
        raise ValueError('Phone originals changed')
    check_lock(out)
    result = {'scope': 'Development engineering regression; one healthy subject is not population validation',
        'endpoint_images': len(selected), 'endpoint_findings': sum(len(r['findings']) for r in selected),
        'endpoint_mismatches': endpoint_mismatches, 'crop_mismatches': crop_mismatches,
        'retained_crop_checks': retained_crop_checks, 'retained_crop_mismatches': retained_crop_mismatches,
        'device_mismatches': device_mismatches, 'max_probability_difference': max_difference,
        'phone_subjects': 1, 'phone_hashes': hashes, 'phone': phone, 'stresses': stresses,
        'malformed_upload_status': malformed.status_code, 'malformed_upload_rejected': malformed_rejected,
        'passes': not endpoint_mismatches and not crop_mismatches and not retained_crop_mismatches and not device_mismatches
            and malformed_rejected and all(not r['hypothetical_flags'] for r in phone) and all(not r['hypothetical_positive'] for r in stresses),
        'thresholds_lock_sha256': file_hash(out / 'thresholds.lock.json'), 'harness_sha256': file_hash(__file__),
        'clinical_release_eligible': False}
    destination.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('endpoint_images', 'endpoint_mismatches', 'crop_mismatches', 'device_mismatches', 'passes')}), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    import torch
    torch.set_num_threads(2)
    verify(ap.parse_args().out)
