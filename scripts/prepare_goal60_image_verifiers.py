"""Prepare isolated TRAIN-derived image verifier fit/calibration/holdout cohorts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_goal60_feature_experiments import sha


def grouped_roles(rows, crop_hashes):
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    owners = {}
    for i, row in enumerate(rows):
        keys = ['patient:' + row['group'], 'original:' + row['sha256']]
        if row['path'] in crop_hashes:
            keys.append('crop:' + crop_hashes[row['path']])
        for key in keys:
            if key in owners:
                parent[root(i)] = root(owners[key])
            else:
                owners[key] = i
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(root(i), []).append(row)
    roles = {}
    for members in groups.values():
        canonical = min(r['group'] for r in members)
        bucket = int(hashlib.sha256(('image-fold-42:' + canonical).encode()).hexdigest(), 16) % 5
        role = 'valid' if bucket == 0 else 'holdout' if bucket == 1 else 'train'
        if any(r['split'] != 'train' for r in members):
            role = 'quarantine'
        for row in members:
            roles[row['path']] = role
    return roles


def prepare(out, features, crops):
    if out.exists():
        raise ValueError('Choose a new experiment directory')
    cache = json.loads(features.read_text())
    for name, digest in cache['fingerprint'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Stale full-image inventory: ' + name)
    crop_manifest = json.loads((crops / 'manifest.json').read_text())
    crop_rows = {r['source'].replace('\\', '/'): r for r in crop_manifest['rows'] if r['split'] == 'train'}
    crop_hashes = {path: sha(crops / row['crop']) for path, row in crop_rows.items()}
    roles = grouped_roles(cache['rows'], crop_hashes)
    out.mkdir(parents=True)
    inventory = {}
    for condition in ('terrys_nails', 'pallor'):
        rows, evaluation, counts = [], [], Counter()
        held_source = 'yolov8-nails-segmentation-ckvkd' if condition == 'terrys_nails' else None
        candidates = [r for r in cache['rows'] if r['split'] == 'train' and roles[r['path']] != 'quarantine']
        available = {source: {label for r in candidates if r['source'] == source for label in r['labels']}
                     for source in {r['source'] for r in candidates}}
        matched = {s for s, labels in available.items() if condition in labels and 'healthy' in labels}
        for r in candidates:
            if r['labels'] not in ([condition], ['healthy']):
                continue
            split = roles[r['path']]
            if r['source'] == held_source or r['source'] not in matched:
                split = 'holdout'
            label = condition if condition in r['labels'] else 'healthy'
            original = ROOT / r['path']
            if sha(original) != r['sha256']:
                raise ValueError('Source image changed')
            entry = {k: r[k] for k in ('path', 'source', 'group', 'sha256', 'labels', 'skin_ita')}
            crop = crop_rows.get(r['path'])
            reason = None if crop else 'no_retained_automatic_crop'
            evaluation.append({**entry, 'split': split, 'crop_failure': reason})
            if split == 'holdout' or reason:
                continue
            if crop['source_sha256'] != r['sha256'] or crop['label'] != label:
                raise ValueError('Crop provenance mismatch')
            source_file = crops / crop['crop']
            prefix = hashlib.sha256(r['source'].encode()).hexdigest()[:16]
            destination = out / condition / split / label / (prefix + '__' + sha(source_file)[:24] + '.png')
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                # Exact identical localized inputs do not get extra sampling weight.
                continue
            shutil.copyfile(source_file, destination)
            rows.append({**entry, 'split': split, 'label': label,
                'crop': destination.relative_to(out / condition).as_posix(), 'crop_sha256': sha(destination)})
            counts[f'{split}:{label}'] += 1
        if any(counts[f'{s}:{label}'] == 0 for s in ('train', 'valid') for label in (condition, 'healthy')):
            raise ValueError('Missing target/negative fit or calibration class')
        manifest = {'version': 1, 'condition': condition, 'rows': rows, 'evaluation_records': evaluation,
            'counts': dict(counts), 'quarantined_train_records': sum(r['split'] == 'train' and roles[r['path']] == 'quarantine' for r in cache['rows']),
            'feature_inventory_sha256': sha(features), 'crop_inventory_sha256': sha(crops / 'manifest.json'),
            'held_source': held_source, 'matched_sources': sorted(matched - {held_source}),
            'exclusions_sha256': None, 'confirmation_used': False,
            'label_basis': 'anemia/Hb proxy, NOT visible pallor' if condition == 'pallor' else 'community dataset Terry labels, NOT independently qualified reviews',
            'initialization': 'ImageNet only; no prior NailIQ candidate initialization',
            'patient_independence_proven': False, 'clinical_release_eligible': False,
            'limitations': ['Known family IDs and exact hashes grouped; unknown patient families may remain',
                'All cohorts derive from historical TRAIN; historical VALID remains a reused development benchmark',
                'Failed localization retained in full-image denominators',
                'Source-matched negatives used where available; target absent does not mean all14 healthy']}
        (out / condition / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        inventory[condition] = {'counts': dict(counts), 'full_image_counts': dict(Counter(r['split'] for r in evaluation)),
            'manifest_sha256': sha(out / condition / 'manifest.json'), 'label_basis': manifest['label_basis']}
    (out / 'inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
    print(json.dumps(inventory), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--features', type=Path, default=ROOT / 'data/raw/goal60_feature_round4_verified/features.json')
    ap.add_argument('--crops', type=Path, default=ROOT / 'data/raw/goal60_runtime_crops_v3')
    args = ap.parse_args()
    prepare(args.out, args.features, args.crops)
