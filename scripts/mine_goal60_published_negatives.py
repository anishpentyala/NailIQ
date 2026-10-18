"""Rank existing expert-assessed TRAIN negatives; never inspect calibration/holdout photos."""
import argparse
import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.published_sign_cohort import load_published_cohort
from ml.eval.image_verifier import StageEvidence, raw_stage
from ml.infer.validation_evidence import file_hash
from scripts.evaluate_goal60_image_verifiers import REFERENCE


def mine(cohort_path, condition, output):
    if output.exists():
        raise ValueError('Preserve previous mining inventory')
    cohort = load_published_cohort(cohort_path)
    if cohort['document'].get('role') != 'development':
        raise ValueError('Mining requires development TRAIN, never fresh confirmation')
    runtime = StageEvidence(REFERENCE)
    metadata = {k: model.metadata for k, model in runtime.models.items()}
    rows = []
    for row in cohort['rows']:
        sign = row['signs'].get(condition, {})
        if row.get('development_split') != 'train' or row['view'] != 'top' or sign.get('status') != 'absent':
            continue
        encoded = base64.b64encode(Path(row['image_path']).read_bytes()).decode()
        branches, _ = runtime.evidence(encoded)
        call = raw_stage({'cache_version': 2, 'branches': branches}, metadata, condition)
        rows.append({'patient_group': row['patient_group'], 'image_path': row['image_path'],
            'image_sha256': row['image_sha256'], 'source': row['source'], 'split': 'train',
            'status': 'absent', 'original_label_reference': sign['original_label_reference'],
            'stage1': call, 'hard_negative': call == 'outside'})
    if load_published_cohort(cohort_path)['sha256'] != cohort['sha256']:
        raise ValueError('Mining source changed')
    rows.sort(key=lambda r: (not r['hard_negative'], r['patient_group']))
    result = {'condition': condition, 'cohort_sha256': cohort['sha256'], 'rows': rows,
        'calibration_images_used': 0, 'holdout_images_used': 0,
        'hard_negative_count': sum(r['hard_negative'] for r in rows),
        'harness_sha256': file_hash(__file__), 'clinical_release_eligible': False,
        'scope': 'TRAIN sampling inventory only; no sign relabeling or trained-model approval'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cohort', type=Path, required=True)
    ap.add_argument('--condition', choices=('terrys_nails', 'pallor'), required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    import torch
    torch.set_num_threads(2)
    result = mine(args.cohort, args.condition, args.out)
    print(json.dumps({'TRAIN_negatives': len(result['rows']), 'hard_negatives': result['hard_negative_count']}))
