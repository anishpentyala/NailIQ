"""Development-only unassessed annotation packets; no clinical labels invented."""
import argparse
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_end_to_end import gather
from ml.eval.eval_color_sensitivity import GHANA, ghana_patient_key

WEAK = ('clubbing', 'koilonychia', 'leukonychia', 'melanonychia', 'pallor', 'terrys_nails', 'lindsays_nails', 'onycholysis')
TASKS = {
    'clubbing': ['side_landmarks', 'repeat_side_capture'],
    'koilonychia': ['side_nail_contour', 'repeat_side_capture'],
    'leukonychia': ['nail_polygon', 'white_lesion_polygons', 'glare_polygons'],
    'melanonychia': ['nail_polygon', 'pigment_polygons', 'shadow_polygons'],
    'pallor': ['visible_pallor_rating', 'capture_quality'],
    'terrys_nails': ['proximal_distal_zones', 'transition_boundary', 'mimic_tags'],
    'lindsays_nails': ['proximal_distal_zones', 'transition_boundary'],
    'onycholysis': ['nail_polygon', 'affected_region_polygons'],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=REPO / 'data/raw/goal60_round2_review')
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Keep previous annotation packets; select a new output directory')
    args.out.mkdir(parents=True)
    exclusion_path = REPO / 'data/raw/goal60_exclusions_v3.json'
    exclusions = json.loads(exclusion_path.read_text())
    rows = []
    for split in ('train', 'valid'):
        for path, labels in sorted(gather(split, exclusions, True, True).items(), key=lambda item: str(item[0])):
            if not any(label in WEAK for label in labels) and labels != {'healthy'}:
                continue
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            source = path.relative_to(REPO).parts[2]
            known_group = ghana_patient_key(path.name, next(iter(labels))) if path.parent == GHANA else None
            rows.append({'image_id': sha[:20], 'path': path.relative_to(REPO).as_posix(), 'sha256': sha,
                         'split': split, 'source': source, 'patient_group': known_group,
                         'patient_group_confirmed': False, 'inherited_labels': sorted(labels),
                         'label_basis': 'community/source labels; visible-sign clinical review pending',
                         'signs': {condition: {'status': 'not_assessed', 'reviewer': None, 'polygons': [],
                                               'landmarks': [], 'notes': ''} for condition in WEAK}})
    with (args.out / 'images.jsonl').open('w', encoding='utf-8') as output:
        for row in rows:
            output.write(json.dumps(row) + '\n')
    preview = args.out / 'previews'
    preview.mkdir()
    for condition in WEAK:
        selected = []
        for split in ('train', 'valid'):
            positives = [row for row in rows if row['split'] == split and condition in row['inherited_labels']]
            controls = [row for row in rows if row['split'] == split and row['inherited_labels'] == ['healthy']]
            # Deterministic review workload; these are images, not a claimed patient cohort.
            selected.extend(sorted(positives, key=lambda row: row['sha256'])[:60])
            selected.extend(sorted(controls, key=lambda row: row['sha256'])[:60])
        directory = args.out / condition
        directory.mkdir()
        with (directory / 'review.csv').open('w', newline='', encoding='utf-8') as output:
            fields = ['image_id', 'path', 'split', 'source', 'patient_group', 'inherited_labels',
                      'status', 'reviewer', 'notes']
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for row in selected:
                writer.writerow({**{key: row[key] for key in fields[:6]},
                                 'status': 'not_assessed', 'reviewer': '', 'notes': ''})
        for page in range(0, len(selected), 24):
            sheet = np.full((6 * 180, 4 * 220, 3), 245, dtype=np.uint8)
            for i, row in enumerate(selected[page:page+24]):
                image = cv2.imread(str(REPO / row['path']))
                if image is None:
                    raise ValueError(f'Unreadable review image: {row["path"]}')
                h, w = image.shape[:2]
                scale = min(210/w, 140/h)
                image = cv2.resize(image, (max(1, round(w*scale)), max(1, round(h*scale))))
                y, x = (i//4)*180, (i%4)*220
                sheet[y:y+image.shape[0], x:x+image.shape[1]] = image
                cv2.putText(sheet, row['image_id'][:12], (x+3,y+157), cv2.FONT_HERSHEY_SIMPLEX, .38,(30,30,30),1)
                cv2.putText(sheet, row['split'], (x+3,y+173), cv2.FONT_HERSHEY_SIMPLEX,.35,(30,30,30),1)
            cv2.imwrite(str(preview / f'{condition}_{page//24+1:02}.jpg'), sheet)
        (directory / 'task.json').write_text(json.dumps({'condition': condition, 'tasks': TASKS[condition],
            'coordinates': 'normalized [x,y] in the ORIGINAL full image', 'reviewer_required': 'qualified clinical reviewer',
            'states': ['present', 'absent', 'indeterminate', 'not_assessed'],
            'images': len(selected), 'no_automatic_negative_labels': True}, indent=2))
    summary = {'images': len(rows), 'counts': dict(Counter(row['split'] for row in rows)),
               'historical_test_included': False, 'clinical_labels_obtained': 0,
               'exclusions_sha256': hashlib.sha256(exclusion_path.read_bytes()).hexdigest(),
               'manifest_sha256': hashlib.sha256((args.out/'images.jsonl').read_bytes()).hexdigest(),
               'patient_independence_proven': False, 'source_images_copied': False,
               'review_previews': 'local research use; do not redistribute without source permission'}
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
