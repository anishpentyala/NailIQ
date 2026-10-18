"""Freeze VALID-selected weights and rules for one final evaluation; never deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_end_to_end import evaluation_fingerprint
from ml.infer import appearance
from scripts.goal60_evidence import same_fingerprint


def candidate_manifest(manifest, rules, evidence):
    if rules.get('min_recall', 0) < 0.6 or not 0 <= rules.get('max_fp', 1) <= 0.05:
        raise ValueError('Selection must retain the 60% recall and 5% false-positive limits')
    result = {**manifest, 'experimental': True, 'deployment_approved': False,
              'validated_roi_modes': [], 'validated_appearance_conditions': [],
              'unvalidated_conditions': sorted(set(rules['unvalidated']) | set(manifest.get('unvalidated_conditions', []))),
              'decision_rules': {c: values for c, values in rules['rules'].items() if c not in appearance.SHAPES},
              'appearance_rules': {c: {'floor': values[0], 'healthy_floor': 0.5}
                                   for c, values in rules['rules'].items() if c in appearance.SHAPES},
              'selection_evidence': evidence}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--locator-dir', type=Path)
    parser.add_argument('--valid-cache', type=Path, required=True)
    parser.add_argument('--rules', type=Path, required=True)
    parser.add_argument('--lineage-dir', type=Path, action='append', default=[])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.model_dir = args.model_dir.resolve()
    if args.locator_dir:
        args.locator_dir = args.locator_dir.resolve()
    metadata_path = args.valid_cache.with_suffix('.meta.json')
    metadata = json.loads(metadata_path.read_text())
    if metadata.get('split') != 'valid' or metadata.get('roi_mode') == 'annotation':
        raise SystemExit('Choose an automatic VALID run, not TEST or annotation-box diagnostics')
    if not same_fingerprint(metadata.get('fingerprint', {}), evaluation_fingerprint(args.model_dir, args.locator_dir)):
        raise SystemExit('VALID evidence is stale; rerun the endpoint before freezing')
    rules = json.loads(args.rules.read_text())
    manifest_path = args.model_dir / 'nail_color_classifier_labels.json'
    if (rules.get('valid_cache_sha256') != hashlib.sha256(args.valid_cache.read_bytes()).hexdigest()
            or rules.get('candidate_manifest_sha256') != hashlib.sha256(manifest_path.read_bytes()).hexdigest()):
        raise SystemExit('Rules must be derived from this exact VALID cache and candidate manifest')
    manifest = json.loads(manifest_path.read_text())
    files = []
    for member in manifest['ensemble']:
        filename = member['weights_file']
        if Path(filename).name != filename or not (args.model_dir / filename).is_file():
            raise SystemExit('Candidate member weights must be local files in its model directory')
        files.append(filename)
    lineage = {}
    for directory in [args.model_dir, *args.lineage_dir]:
        directory = directory.resolve()
        for member in manifest['ensemble']:
            path = directory / f"training_{member['backbone']}.json"
            source_weights = directory / member['weights_file']
            if not path.is_file() or not source_weights.is_file():
                continue
            source_hash = hashlib.sha256(source_weights.read_bytes()).hexdigest()
            if source_hash != hashlib.sha256((args.model_dir / member['weights_file']).read_bytes()).hexdigest():
                raise SystemExit('Training lineage weights do not match this frozen member')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if member['backbone'] in lineage and lineage[member['backbone']]['metadata_sha256'] != digest:
                raise SystemExit('Conflicting training lineage for the same member')
            lineage[member['backbone']] = {'path': str(path), 'metadata_sha256': digest, 'weights_sha256': source_hash}
    evidence = {'valid_cache': str(args.valid_cache.resolve()),
                'valid_cache_sha256': hashlib.sha256(args.valid_cache.read_bytes()).hexdigest(),
                'rules_sha256': hashlib.sha256(args.rules.read_bytes()).hexdigest(),
                'validation_metadata': metadata, 'training_lineage': lineage, 'test_evaluated': False,
                'scope': 'Frozen experiment; existing condition and ROI validation gates remain active'}
    frozen = candidate_manifest(manifest, rules, evidence)
    if args.out.exists():
        raise SystemExit('Choose a new output directory; frozen candidates are never overwritten')
    args.out.mkdir(parents=True)
    for filename in files:
        shutil.copy2(args.model_dir / filename, args.out / filename)
    (args.out / 'nail_color_classifier_labels.json').write_text(json.dumps(frozen, indent=2))
    shutil.copy2(args.rules, args.out / 'selected_rules.json')
    (args.out / 'lineage').mkdir()
    for backbone, entry in lineage.items():
        shutil.copy2(entry['path'], args.out / 'lineage' / f'{backbone}.json')
    if args.locator_dir:
        locator = args.out / 'locator'
        locator.mkdir()
        for path in args.locator_dir.iterdir():
            if path.suffix in {'.pt', '.json'}:
                shutil.copy2(path, locator / path.name)
    print(json.dumps({'frozen': str(args.out.resolve()), 'unvalidated': frozen['unvalidated_conditions'],
                      'deployment_approved': False}), flush=True)


if __name__ == '__main__':
    main()
