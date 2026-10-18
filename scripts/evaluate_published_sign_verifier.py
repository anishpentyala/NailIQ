"""Evaluate partial published sign labels without inventing paired or healthy labels."""
import argparse
import base64
from collections import Counter
import json
import os
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.published_sign_cohort import load_published_cohort
from ml.eval.image_verifier import raw_stage, shadow, verifier_score, runtime_reference
from ml.eval.eval_color_sensitivity import create_eval_client
from ml.eval.eval_end_to_end import wilson_interval
from ml.infer.routing import RoutingRuntime
from ml.infer.validation_evidence import file_hash
from scripts.evaluate_goal60_image_verifiers import REFERENCE, check_lock, load_models
from scripts.report_goal60 import CONDITIONS


def assessed_metrics(rows, condition, field):
    def sign(r):
        return r['signs'].get(condition, {}).get('status', 'unknown')
    positives = [r for r in rows if sign(r) == 'present']
    negatives = [r for r in rows if sign(r) == 'absent']
    tp = sum(r[field][condition] == 'outside' for r in positives)
    fp = sum(r[field][condition] == 'outside' for r in negatives)
    return {'positive_n': len(positives), 'tp': tp, 'recall': tp / len(positives) if positives else None,
        'recall_interval': wilson_interval(tp, len(positives)), 'target_absent_n': len(negatives), 'fp': fp,
        'fp_rate': fp / len(negatives) if negatives else None, 'fp_interval': wilson_interval(fp, len(negatives)),
        'positive_inconclusive': sum(r[field][condition] == 'inconclusive' for r in positives),
        'negative_inconclusive': sum(r[field][condition] == 'inconclusive' for r in negatives),
        'unknown_n': sum(sign(r) == 'unknown' for r in rows),
        'indeterminate_n': sum(sign(r) == 'indeterminate' for r in rows)}


def evaluate(cohort_path, models_out, output, device):
    if output.exists():
        raise ValueError('Preserve previous evaluation')
    cohort = load_published_cohort(cohort_path)
    if cohort['document'].get('role') != 'holdout':
        raise ValueError('Explicit published research holdout required; never training/calibration records')
    lock, _ = check_lock(models_out)
    models = load_models(models_out, device)
    used_images, used_patients = set(), set()
    for c in models:
        inventory = json.loads((models_out / c / 'manifest.json').read_text())
        for row in inventory['rows']:
            used_images.add(row.get('image_sha256', row.get('sha256')))
            if row.get('patient_group'):
                used_patients.add(row['patient_group'])
    if any(r['image_sha256'] in used_images or r['patient_group'] in used_patients for r in cohort['rows']):
        raise ValueError('Published holdout overlaps verifier training/calibration')
    reference = runtime_reference(REFERENCE, device)
    os.environ['NAILIQ_ROUTING_MANIFEST'] = str(reference.resolve())
    runtime = RoutingRuntime(reference)
    metadata = {k: m.metadata for k, m in runtime.models.items()}
    _, client = create_eval_client()
    _, placeholder = cv2.imencode('.jpg', np.full((64, 64, 3), 128, np.uint8))
    side = base64.b64encode(placeholder).decode()
    rows = []
    for original in cohort['rows']:
        actual = {c: 'inconclusive' for c in CONDITIONS}
        proposed = dict(actual)
        diagnostics = {}
        failure = 'top_view_unavailable'
        if original['view'] == 'top':
            top = base64.b64encode(Path(original['image_path']).read_bytes()).decode()
            response = client.post('/analyze', json={'side_image': side, 'top_image': top})
            if response.status_code == 200:
                body = response.get_json()
                actual.update({f['label']: f['verdict'] for f in body['findings']})
                proposed = dict(actual)
                branches = body.get('overlay', {}).get('routing_evidence', {})
                failure = None
                for c, model in models.items():
                    probability, reason = verifier_score(top, branches, model, c)
                    stage = raw_stage({'cache_version': 2, 'branches': branches}, metadata, c) if branches else 'inconclusive'
                    result = shadow(actual[c], stage, probability, lock['thresholds'][c])
                    proposed[c] = result['hypothetical_shown']
                    diagnostics[c] = {'stage1': stage, 'probability': probability, 'failure': reason}
            else:
                failure = f'http_{response.status_code}'
        rows.append({**original, 'actual': actual, 'hypothetical': proposed,
                     'failure': failure, 'verifiers': diagnostics})
    if load_published_cohort(cohort_path)['sha256'] != cohort['sha256']:
        raise ValueError('Published originals changed')
    result = {'scope': 'Partial published-label research endpoint/shadow comparison; unavailable side is a blank placeholder',
        'clinical_release_eligible': False, 'geometry_validated': False, 'paired_capture_validated': False,
        'cohort_sha256': cohort['sha256'], 'thresholds_lock_sha256': file_hash(models_out / 'thresholds.lock.json'),
        'all14': {c: {field: assessed_metrics(rows, c, field) for field in ('actual', 'hypothetical')} for c in CONDITIONS},
        'sources': {s: {c: assessed_metrics([r for r in rows if r['source'] == s], c, 'hypothetical') for c in CONDITIONS}
                    for s in sorted({r['source'] for r in rows})},
        'verified_all_signs_absent_n': sum(r['verified_all_signs_absent'] for r in rows),
        'failure_counts': dict(Counter(r['failure'] for r in rows if r['failure'])), 'rows': rows,
        'limitations': ['All original positives retained, including localization/HTTP/view failures',
            'Unknown and indeterminate labels reported separately; never reclassified as negatives',
            'Target-negative FP is not the all-sign healthy scan FP rate',
            'Original assessor claims and source reuse permission still require independent audit']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cohort', type=Path, required=True)
    ap.add_argument('--models', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--device', choices=('cpu', 'cuda:0'), default='cuda:0')
    args = ap.parse_args()
    import torch
    torch.set_num_threads(2)
    result = evaluate(args.cohort, args.models, args.out, args.device)
    print(json.dumps({'evaluated': len(result['rows']), 'clinical_release_eligible': False}))
