"""Build research-only crops from partial, already-published visible-sign labels."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.published_sign_cohort import load_published_cohort
from ml.infer.validation_evidence import file_hash, identity
from scripts.build_goal60_reviewed_specialist import reviewed_crop


def build(cohort_path, condition, output):
    cohort = load_published_cohort(cohort_path)
    if cohort['document'].get('role') != 'development':
        raise ValueError('Only development labels may supply training or calibration')
    if output.exists():
        raise ValueError('Preserve previous data; choose a new output directory')
    prepared, failures, evaluation = [], [], []
    for row in cohort['rows']:
        split = row.get('development_split')
        if split not in ('train', 'valid', 'holdout'):
            raise ValueError('Preassign each patient research split')
        sign = row['signs'].get(condition)
        status = sign['status'] if sign else 'unknown'
        entry = {'patient_group': row['patient_group'], 'source': row['source'],
                 'image_path': row['image_path'], 'image_sha256': row['image_sha256'],
                 'split': split, 'status': status, 'view': row['view'],
                 'verified_all_signs_absent': row['verified_all_signs_absent']}
        reason = None
        crop = None
        if status not in ('present', 'absent'):
            reason = status + '_label'
        elif row['view'] != 'top':
            reason = 'top_view_unavailable'
        elif split != 'holdout':
            crop, reason = reviewed_crop(Path(row['image_path']))
        # All originals, including failed positives, stay in the evaluation manifest.
        evaluation.append({**entry, 'crop_failure': reason})
        if reason or split == 'holdout':
            failures.append({**entry, 'reason': reason or 'reserved_holdout'})
            continue
        label = condition if status == 'present' else 'healthy'
        prefix = identity(row['source'])[:16]
        name = prefix + '__' + identity(row['patient_group'])[:24] + '.png'
        prepared.append({**entry, 'label': label, 'source_prefix': prefix,
            'original_label_reference': sign['original_label_reference'],
            'crop': f'{split}/{label}/{name}', '_pixels': crop})
    source_counts = Counter((r['source'], r['split'], r['label']) for r in prepared)
    matched = {r['source'] for r in prepared if all(source_counts[(r['source'], s, label)]
               for s in ('train', 'valid') for label in (condition, 'healthy'))}
    for row in prepared:
        if row['source'] not in matched:
            failures.append({k: v for k, v in row.items() if k != '_pixels'} | {'reason': 'unmatched_source'})
    prepared = [r for r in prepared if r['source'] in matched]
    counts = Counter((r['split'], r['label']) for r in prepared)
    if any(counts[(s, label)] == 0 for s in ('train', 'valid') for label in (condition, 'healthy')):
        raise ValueError('TRAIN and calibration VALID need explicit present and absent labels')
    if load_published_cohort(cohort_path)['sha256'] != cohort['sha256']:
        raise ValueError('Published cohort changed during crop extraction')
    output.mkdir(parents=True)
    for row in prepared:
        pixels = row.pop('_pixels')
        path = output / row['crop']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(path), pixels):
            raise RuntimeError('Crop write failed')
        row['crop_sha256'] = file_hash(path)
    manifest = {'version': 1, 'condition': condition, 'label_basis': 'documented published visible-sign assessments',
        'cohort_sha256': cohort['sha256'], 'harness_sha256': file_hash(__file__),
        'crop_mode': 'original bytes; automatic legacy localization', 'exclusions_sha256': None,
        'confirmation_used': False, 'clinical_release_eligible': False,
        'rows': prepared, 'failures': failures, 'evaluation_records': evaluation, 'matched_sources': sorted(matched),
        'limitations': ['Source documentation is not independently verified by the importer',
            'Target absent is not all-signs healthy', 'Failed positives remain strict evaluation misses',
            'Partial top-only labels cannot authorize angle/depth or clinical deployment']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--condition', choices=('terrys_nails', 'pallor'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.cohort, args.condition, args.out)
    print(json.dumps({'crops': len(result['rows']), 'evaluation_records': len(result['evaluation_records'])}))
