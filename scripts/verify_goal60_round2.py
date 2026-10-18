"""Verify shown/pre-policy replay and report source and baseline comparisons."""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.infer.routing import RoutingRuntime, digest, merge_shape
from scripts.run_goal60_round2 import checked
from scripts.report_goal60 import CONDITIONS, healthy_summary, score
from ml.eval.routed_replay import coverage_ok, replay
from ml.eval.eval_end_to_end import metrics
from ml.eval.withholding_checks import acceptance


def verify(cache, manifest, output):
    records = checked(cache, manifest)
    runtime = RoutingRuntime(manifest)
    metadata = {key: model.metadata for key, model in runtime.models.items()}
    errors = []
    unverified_geometry = 0
    for record in records:
        for condition in CONDITIONS:
            finding = runtime.selected(record['branches'], condition)
            observed = record['findings'][condition]
            # Reliable geometry remains authoritative; no synthetic angle is replayed.
            if condition in ('clubbing', 'koilonychia') and not record['appearance_eligible'][condition]:
                original = record.get('geometry_evidence', {}).get(condition)
                if original is None:
                    unverified_geometry += 1
                    continue
                finding = merge_shape(original, finding)
            before = finding.get('unvalidated_verdict', finding['verdict'])
            if before != observed['verdict'] or finding['verdict'] != observed['shown']:
                errors.append({'path': record['path'], 'condition': condition, 'type': 'verdict'})
            if observed.get('route_id') is not None and observed['route_id'] != finding['route_id']:
                errors.append({'path': record['path'], 'condition': condition, 'type': 'route'})
    if errors:
        raise ValueError(f'Replay mismatches: {len(errors)}; {errors[:5]}')
    baseline = metrics(records, lambda r, c: replay(r, c, metadata, {'model': 'baseline', 'route': 'legacy'})[0])
    selected = score(records)
    sources = sorted({Path(record['path']).parts[2] for record in records})
    result = {'scope': 'VALID development only; no historical TEST evaluation',
              'cache_sha256': digest(cache), 'manifest_sha256': digest(manifest),
              'harness_sha256': digest(__file__), 'images': len(records),
              'findings_checked': len(records) * len(CONDITIONS), 'mismatches': 0,
              'unverified_geometry': unverified_geometry,
              'pre_policy': selected, 'shown': score(records, True),
              'healthy_scans': {'pre_policy': healthy_summary(records), 'shown': healthy_summary(records, True)},
              'common_baseline': baseline,
              'coverage_constraints': {c: coverage_ok(selected[c], baseline[c]) for c in CONDITIONS},
              'by_source': {source: score([r for r in records if Path(r['path']).parts[2] == source]) for source in sources}}
    anchor = REPO / 'ml/eval/goal60_round2_selected_gpu_valid.json'
    result['strict_displayed'] = acceptance(records, json.loads(anchor.read_text()), True)
    result['strict_reference_sha256'] = digest(anchor)
    result['bundle_sha256'] = runtime.bundle_sha256
    result['non_regression_passed'] = result['strict_displayed']['non_regression_passed']
    old_path = REPO / 'ml/eval/goal60_final_frozen_valid.json'
    if old_path.is_file():
        old = {r['path']: r for r in json.loads(old_path.read_text())}
        compared, different = 0, []
        for record in records:
            previous = old.get(record['path'])
            if previous is None or previous['labels'] != record['labels']:
                raise ValueError('Common baseline input membership differs from historical v3 VALID')
            for condition in CONDITIONS:
                if condition not in previous['findings']:
                    continue
                compared += 1
                value, _ = replay(record, condition, metadata, {'model': 'baseline', 'route': 'legacy'})
                if value != previous['findings'][condition]['verdict']:
                    different.append({'path': record['path'], 'condition': condition,
                                      'old': previous['findings'][condition]['verdict'], 'new': value})
        result['historical_baseline_comparison'] = {'cache_sha256': digest(old_path),
            'compared_findings': compared, 'mismatches': len(different), 'differences': different,
            'purpose': 'contract regression comparison; old cache is historical, not fresh confirmation'}
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps({'images': len(records), 'mismatches': 0,
                     'coverage_constraints': result['coverage_constraints'],
                     'historical_baseline_mismatches': result.get('historical_baseline_comparison', {}).get('mismatches')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    verify(args.cache, args.manifest, args.out)
