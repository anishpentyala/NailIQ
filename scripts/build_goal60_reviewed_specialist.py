"""Build patient-grouped specialist crops from qualified visible-sign reviews only."""
import argparse
import base64
import binascii
from collections import Counter
import json
from pathlib import Path
import sys
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.confirmation_cohort import load_cohort
from ml.infer.validation_evidence import file_hash, identity
from ml.infer import nail_region
from ml.infer.color_classifier import _crop_to_bbox
from ml.infer.preprocessing import decode_base64_image, extract_best_contour, focus_score, is_flat_frame, BLUR_THRESHOLD


def reviewed_crop(path):
    try:
        image = decode_base64_image(base64.b64encode(path.read_bytes()).decode())
    except (ValueError, binascii.Error, cv2.error):
        return None, 'invalid_image'
    if image is None:
        return None, 'invalid_image'
    if is_flat_frame(image):
        return None, 'camera_feed_blank'
    if focus_score(image) < BLUR_THRESHOLD:
        return None, 'too_blurry'
    contour, validation = extract_best_contour(image)
    if not validation['is_valid']:
        return None, validation['reason']
    region, reason = nail_region.compute_nail_region(image, contour)
    return (None, reason) if reason else (_crop_to_bbox(image, region['bbox_norm']), None)


def build(cohort_path, condition, output):
    cohort = load_cohort(cohort_path)
    if cohort['document']['role'] != 'development':
        raise ValueError('Fresh confirmation cannot supply training or calibration images')
    if output.exists():
        raise ValueError('Preserve previous training data; choose another output directory')
    rows, failures, counts = [], [], Counter()
    for patient in cohort['rows']:
        split = patient.get('development_split')
        if split not in ('train', 'valid'):
            raise ValueError('Preassign each development patient to train or valid before building crops')
        sign = patient['signs'][condition]
        if sign['status'] == 'indeterminate':
            failures.append({'patient_group': patient['patient_group'], 'reason': 'indeterminate_label'})
            continue
        label = condition if sign['status'] == 'present' else 'healthy'
        # Specialist healthy means target absent; endpoint controls require all
        # fourteen signs reviewed absent.
        source = identity(patient['source'])[:16]
        crop, reason = reviewed_crop(Path(patient['photos']['top']['path']))
        if reason:
            failures.append({'patient_group': patient['patient_group'], 'reason': reason})
            continue
        name = source + '__' + identity(patient['patient_group'])[:24] + '.png'
        rows.append({'patient_group': patient['patient_group'], 'source': patient['source'],
            'source_prefix': source, 'source_sha256': patient['photos']['top']['sha256'],
            'split': split, 'label': label, 'status': sign['status'], 'reviewer': sign['reviewer'],
            'crop': f'{split}/{label}/{name}', '_pixels': crop})
        counts[(split, source, label)] += 1
    matched = {r['source_prefix'] for r in rows if all(counts[(s, r['source_prefix'], label)]
               for s in ('train', 'valid') for label in ('healthy', condition))}
    if not matched:
        raise ValueError('Reviewed source-matched TRAIN and VALID need both target-present and target-absent patients')
    output.mkdir(parents=True)
    saved = []
    for row in rows:
        if row['source_prefix'] not in matched:
            failures.append({'patient_group': row['patient_group'], 'reason': 'unmatched_source'})
            continue
        crop = row.pop('_pixels')
        path = output / row['crop']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(path), crop):
            raise RuntimeError('Could not save a reviewed development crop')
        row['crop_sha256'] = file_hash(path)
        saved.append(row)
    if load_cohort(cohort_path)['sha256'] != cohort['sha256']:
        raise ValueError('Reviewed data changed during crop building')
    manifest = {'version': 1, 'condition': condition, 'label_basis': 'qualified visible-sign review',
        'cohort_sha256': cohort['sha256'], 'harness_sha256': file_hash(__file__),
        'crop_mode': 'legacy localization on the submitted capture bytes; no simulated framing',
        'confirmation_used': False, 'exclusions_sha256': None, 'rows': saved,
        'matched_sources': sorted(matched), 'failures': failures,
        'limitations': ['Specialist healthy means target absent, not absence of every sign',
            'Failed localization omitted from training remains a miss in endpoint evaluation',
            'Crop performance cannot authorize displayed results']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'saved_crops': len(saved), 'skipped': len(failures), 'condition': condition}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--condition', choices=('pallor', 'terrys_nails', 'leukonychia', 'clubbing', 'koilonychia'), default='pallor')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.cohort, args.condition, args.out)
