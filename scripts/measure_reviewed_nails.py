"""Measure reviewed polygons offline; never infer labels or production verdicts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.infer.review_measurements import lindsay_zones, onycholysis_area


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    outputs, skipped = [], 0
    for line in args.reviews.read_text().splitlines():
        row = json.loads(line)
        eligible = {c: row.get('signs', {}).get(c, {}) for c in ('onycholysis', 'lindsays_nails')}
        eligible = {c: s for c,s in eligible.items() if s.get('reviewer') and s.get('status') in ('present', 'absent')}
        if not eligible or not row.get('nail_polygons'):
            skipped += 1
            continue
        path = (REPO/row['path']).resolve()
        if not path.is_relative_to(REPO) or row.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Original image path/hash mismatch')
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError('Reviewed image is unreadable')
        for condition, annotation in eligible.items():
            if condition == 'onycholysis':
                if 'affected_polygons' not in annotation or (annotation['status'] == 'present' and not annotation['affected_polygons']):
                    continue
                measurement = onycholysis_area(image.shape, row['nail_polygons'], annotation['affected_polygons'])
            else:
                if not annotation.get('proximal_polygons') or not annotation.get('distal_polygons'):
                    continue
                measurement = lindsay_zones(image, row['nail_polygons'], annotation['proximal_polygons'], annotation['distal_polygons'])
            outputs.append({'image_id': row['image_id'], 'split': row['split'], 'condition': condition,
                'reviewed_status': annotation['status'], 'reviewer': annotation['reviewer'],
                'patient_group': row.get('patient_group'), 'measurement': measurement,
                'source_sha256': row['sha256']})
    result = {'scope': 'offline reviewed-mask measurements; no calibrated thresholds or new predictions',
              'review_manifest_sha256': hashlib.sha256(args.reviews.read_bytes()).hexdigest(),
              'skipped_unreviewed_or_missing_masks': skipped, 'measurements': outputs}
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps({'measurements': len(outputs), 'skipped': skipped, 'validated': False}))


if __name__ == '__main__':
    main()
