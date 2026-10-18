"""VALID-only local round: fixed routes, common coverage baseline, immutable rules."""
import argparse
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_end_to_end import evaluation_fingerprint, metrics, gather
from ml.eval.routed_replay import coverage_ok, replay
from ml.eval.tune_color_decision import FLOORS, OVRS, SUPPORTS
from ml.infer.routing import RoutingRuntime, digest
from scripts.goal60_evidence import same_fingerprint
from scripts.report_goal60 import CONDITIONS, healthy_summary

RAW = REPO / 'data/raw'
EVAL = REPO / 'ml/eval'
PASSING = {'cyanosis', 'beaus_lines', 'muehrckes_lines', 'splinter_hemorrhages', 'pitting', 'onychogryphosis'}


def base_spec():
    return {'version': 1, 'experimental': True, 'deployment_approved': False,
            'models': {'baseline': '../goal60_selected_frozen_v3'}, 'locator': '../goal60_nail_locator',
            'conditions': {c: {'model': 'baseline', 'route': 'legacy'} for c in CONDITIONS},
            'protocol': 'docs/goal60-round2-protocol.md'}


def checked(cache, manifest):
    records = json.loads(cache.read_text())
    meta = json.loads(cache.with_suffix('.meta.json').read_text())
    if meta.get('split') != 'valid' or meta.get('cache_version') != 2 or meta.get('roi_mode') == 'annotation':
        raise ValueError('Selection requires automatic version-two VALID evidence')
    if meta.get('routing_sha256') != digest(manifest):
        raise ValueError('Routing manifest changed after endpoint scoring')
    if not same_fingerprint(meta['fingerprint'], evaluation_fingerprint(routing_manifest=manifest)):
        raise ValueError('Stale code or weight evidence')
    exclusions = RAW / 'goal60_exclusions_v3.json'
    if meta.get('exclusions_sha256') != digest(exclusions):
        raise ValueError('Exclusions changed')
    current = gather('valid', json.loads(exclusions.read_text()), meta.get('include_authorized', False), meta.get('include_shapes', False))
    identity = [(str(path.relative_to(REPO)), sorted(labels), digest(path))
                for path, labels in sorted(current.items(), key=lambda item: str(item[0]))]
    if [(r['path'], r['labels']) for r in records] != [(p, labels) for p, labels, _ in identity]:
        raise ValueError('Current input membership or labels changed')
    if meta.get('input_label_manifest_sha256') != hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest():
        raise ValueError('Input/label manifest changed')
    return records


def select(cache, manifest, output):
    records = checked(cache, manifest)
    spec = json.loads(manifest.read_text())
    runtime = RoutingRuntime(manifest)
    metadata = {key: model.metadata for key, model in runtime.models.items()}
    baseline = metrics(records, lambda r, c: replay(r, c, metadata, {'model': 'baseline', 'route': 'legacy'})[0])
    rows = {}
    chosen = copy.deepcopy(spec)
    for condition in CONDITIONS:
        condition_records = [{**r, 'findings': {condition: r['findings'][condition]}} for r in records
                             if condition in r['labels'] or r['labels'] == ['healthy']]
        defaults = {'model': 'baseline', 'route': 'legacy'}
        configs = [defaults]
        if condition not in PASSING:
            for route in ('legacy', 'detector', 'detector_fallback'):
                configs.append({'model': 'baseline', 'route': route})
            if condition == 'terrys_nails':
                for model in metadata:
                    if condition not in metadata[model].get('app_conditions', []):
                        continue
                    for route, rule in itertools.product(('legacy', 'detector', 'detector_fallback'), itertools.product(FLOORS, OVRS, SUPPORTS)):
                        inherited = metadata[model].get('decision_rules', {}).get(condition, [0.45, None, None])
                        values = [inherited[i] if value is None else value for i, value in enumerate(rule)]
                        configs.append({'model': model, 'route': route, 'rules': values})
            if condition == 'pallor' and 'pallor' in metadata:
                for floor in [round(.25 + i * .05, 2) for i in range(14)]:
                    configs.append({'model': 'pallor', 'route': 'legacy', 'rules': [floor, None, 0.05]})
        candidates = []
        for config in configs:
            row = metrics(condition_records, lambda r, c: replay(r, condition, metadata, config)[0])[condition]
            cap = 0.03 if condition == 'terrys_nails' else 0.05
            admissible = coverage_ok(row, baseline[condition]) and row['fp_rate'] is not None and row['fp_rate'] <= cap
            if condition == 'terrys_nails':
                admissible = admissible and row['recall'] is not None and row['recall'] >= 0.6
            candidates.append({'config': config, 'metrics': row, 'admissible': admissible})
        valid = [r for r in candidates if r['admissible']]
        complexity = lambda cfg: int(cfg['route'] != 'legacy') + int('rules' in cfg) + int(cfg['model'] != 'baseline')
        pick = max(valid, key=lambda r: (r['metrics']['recall'] or 0, -(r['metrics']['fp_rate'] or 0),
                                        r['metrics']['healthy_correct_rate'] or 0, -complexity(r['config']))) if valid else candidates[0]
        improves = ((pick['metrics']['recall'] or 0) > (baseline[condition]['recall'] or 0)
                    or ((pick['metrics']['recall'] or 0) == (baseline[condition]['recall'] or 0)
                        and (pick['metrics']['fp_rate'] or 0) < (baseline[condition]['fp_rate'] or 0)))
        if condition in PASSING or not improves:
            pick = candidates[0]
        chosen['conditions'][condition] = pick['config']
        rows[condition] = {'baseline': baseline[condition], 'selected': pick,
                           'automatic_route_diagnostics': [r for r in candidates if 'rules' not in r['config']],
                           'candidate_count': len(candidates)}
    routed = metrics(records, lambda r, c: replay(r, c, metadata, chosen['conditions'][c])[0])
    output.write_text(json.dumps(chosen, indent=2))
    result = {'scope': 'VALID development selection, not confirmation or deployment', 'conditions': rows,
              'selected_metrics': routed, 'common_baseline': 'frozen EfficientNet/legacy',
              'coverage_slack': 0.02, 'terry_development_fp_cap': 0.03,
              'cache_sha256': digest(cache), 'routing_sha256': digest(output), 'historical_test_used': False}
    output.with_suffix('.selection.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({c: {'route': chosen['conditions'][c], 'recall': routed[c]['recall'], 'fp': routed[c]['fp_rate']}
                      for c in CONDITIONS}), flush=True)


def parity(cache, manifest):
    records = checked(cache, manifest)
    runtime = RoutingRuntime(manifest)
    metadata = {key: model.metadata for key, model in runtime.models.items()}
    errors = []
    spec = json.loads(manifest.read_text())
    for record in records:
        for condition in CONDITIONS:
            verdict, _ = replay(record, condition, metadata, spec['conditions'][condition])
            if verdict != record['findings'][condition]['verdict']:
                errors.append((record['path'], condition, verdict, record['findings'][condition]['verdict']))
    if errors:
        raise ValueError(f'Endpoint/replay mismatch: {errors[:10]} ({len(errors)} total)')
    result = {'images': len(records), 'findings_checked': len(records) * len(CONDITIONS), 'mismatches': 0,
              'cache_sha256': digest(cache), 'manifest_sha256': digest(manifest)}
    cache.with_suffix('.parity.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'select', 'parity'])
    parser.add_argument('--manifest', type=Path, default=RAW / 'goal60_round2/routing.json')
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--specialist', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        spec = base_spec()
        if args.specialist:
            spec['models']['pallor'] = '../goal60_round2_pallor'
            spec['models']['mobile'] = '../goal60_authorized_mobilenet_frozen'
            spec['models']['ensemble'] = '../goal60_authorized_ensemble'
        if args.manifest.exists():
            raise ValueError('Preserve existing experiment; choose another manifest path')
        args.manifest.write_text(json.dumps(spec, indent=2))
    elif args.action == 'select':
        select(args.cache, args.manifest, args.out)
    else:
        parity(args.cache, args.manifest)


if __name__ == '__main__':
    main()
