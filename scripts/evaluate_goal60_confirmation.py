"""Lock and evaluate one fresh reviewed cohort; issue no grant without every gate."""
import argparse
import base64
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.confirmation_cohort import load_cohort, separate_cohorts, template
from ml.eval.withholding_checks import acceptance, subgroup_checks, TARGETS
from ml.eval.eval_end_to_end import evaluation_fingerprint
from ml.infer.routing import RoutingRuntime, merge_shape, rules_for
from ml.infer.validation_evidence import context, file_hash, identity, REQUIRED_CHECKS
from scripts.report_goal60 import CONDITIONS, score

LEDGER = ROOT / 'data/raw/goal60_confirmation_ledger'
UNLOCKS = tuple(c for c in TARGETS if c not in ('cyanosis', 'beaus_lines', 'muehrckes_lines',
    'splinter_hemorrhages', 'pitting', 'onychogryphosis'))


def consumption_paths(cohort):
    hashes = {p['sha256'] for row in cohort['rows'] for p in row['photos'].values()}
    patients = {identity({'source': row['source'], 'patient_group': row['patient_group']}) for row in cohort['rows']}
    return sorted([LEDGER / ('photo-' + sha + '.json') for sha in hashes]
                  + [LEDGER / ('patient-' + sha + '.json') for sha in patients])


def context_metrics(records, scope):
    subset = [r for r in records if r.get('validation_contexts', {}).get(scope['condition']) == scope]
    if not subset:
        return {'context': scope, 'positive_patients': 0, 'healthy_patients': 0,
                'recall': None, 'healthy_fp_rate': None}
    metrics = score(subset, True)[scope['condition']]
    return {'context': scope, 'positive_patients': metrics['pos']['n'],
        'healthy_patients': metrics['healthy']['n'], 'recall': metrics['recall'], 'healthy_fp_rate': metrics['fp_rate']}


def evaluate(rows, manifest, planned=(), client=None):
    if manifest:
        os.environ['NAILIQ_ROUTING_MANIFEST'] = str(manifest.resolve())
    else:
        os.environ.pop('NAILIQ_ROUTING_MANIFEST', None)
    if client is None:
        from ml.eval.eval_color_sensitivity import create_eval_client
        _, client = create_eval_client()
    runtime = RoutingRuntime(manifest) if manifest else None
    results, scopes, mismatches = [], {}, []
    for row in rows:
        payload = {view + '_image': base64.b64encode(Path(row['photos'][view]['path']).read_bytes()).decode()
                   for view in ('side', 'top')}
        if row.get('top_nail_bbox') is not None:
            payload['top_nail_bbox'] = row['top_nail_bbox']
        response = client.post('/analyze', json=payload)
        findings, body = {}, response.get_json() if response.status_code == 200 else {}
        for finding in body.get('findings', []):
            condition = finding['label']
            value = finding['verdict']
            findings[condition] = {**finding, 'shown': value}
        for condition in CONDITIONS:
            findings.setdefault(condition, {'verdict': 'inconclusive', 'shown': 'inconclusive',
                'failure_reason': f'endpoint_failure_{response.status_code}'})
        if runtime and response.status_code == 200:
            overlay = body.get('overlay', {})
            branches = overlay.get('routing_evidence', {})
            for condition in CONDITIONS:
                actual = runtime.selected(branches, condition)
                if condition in ('clubbing', 'koilonychia'):
                    original = overlay.get('geometry_evidence', {}).get(condition)
                    if original is None:
                        mismatches.append((row['path'], condition, 'missing_geometry'))
                        continue
                    actual = merge_shape(original, actual)
                observed = next((f for f in body['findings'] if f['label'] == condition), {})
                if (actual['verdict'], actual.get('route_id')) != (observed.get('verdict'), observed.get('route_id')):
                    mismatches.append((row['path'], condition, 'replay'))
        row_contexts = {}
        if runtime and response.status_code == 200:
            for condition in TARGETS:
                selected = next((f for f in body['findings'] if f['label'] == condition), {})
                key = selected.get('route_id')
                if key in branches:
                    config = runtime.spec['conditions'][condition]
                    scope = context(runtime, condition, config, branches[key],
                        rules_for(runtime.models[config['model']].metadata, condition, config.get('rules')), runtime.bundle_sha256)
                    row_contexts[condition] = scope
                    if scope in planned:
                        findings[condition]['shown'] = selected.get('unvalidated_verdict', selected['verdict'])
        results.append({**{k: row[k] for k in ('path', 'labels', 'source', 'skin_tone_band')}, 'findings': findings,
            'http_status': response.status_code, 'signs': row['signs'], 'validation_contexts': row_contexts})
    return results, list(planned), mismatches


def lock(args):
    os.environ.pop('NAILIQ_ROUTING_MANIFEST', None)
    development, cohort = load_cohort(args.development), load_cohort(args.cohort)
    separate_cohorts(development, cohort)
    if any(path.exists() for path in consumption_paths(cohort)):
        raise ValueError('This confirmation cohort has already been consumed')
    from ml.eval.eval_end_to_end import gather
    known = {file_hash(photo) for split in ('train', 'valid', 'test')
             for photo in gather(split, None, True, True)}
    if any(p['sha256'] in known for row in cohort['rows'] for p in row['photos'].values()):
        raise ValueError('Confirmation contains an existing training/development/archive photo')
    runtime = RoutingRuntime(args.candidate)
    proposed = json.loads(args.context_plan.read_text())
    scopes = proposed.get('contexts', [])
    if (proposed.get('bundle_sha256') != runtime.bundle_sha256 or not scopes
            or any(not isinstance(scope, dict) or scope.get('condition') not in UNLOCKS for scope in scopes)):
        raise ValueError('Seal exact proposed scopes for the six unlock signs during development')
    reference = RoutingRuntime(args.reference)
    record = {'version': 1, 'bundle_sha256': runtime.bundle_sha256, 'cohort_sha256': cohort['sha256'],
        'development_sha256': development['sha256'], 'reference_bundle_sha256': reference.bundle_sha256,
        'reference_execution_fingerprint': {p: file_hash(p) for p in reference.dependencies},
        'candidate_execution_fingerprint': {p: file_hash(p) for p in runtime.dependencies},
        'production_fingerprint': evaluation_fingerprint(),
        'planned_contexts': scopes, 'confirmation_used': False}
    if args.out.exists():
        raise ValueError('Preserve the existing confirmation lock')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2))


def run(args):
    cohort, development = load_cohort(args.cohort), load_cohort(args.development)
    separate_cohorts(development, cohort)
    sealed = json.loads(args.lock.read_text())
    runtime = RoutingRuntime(args.candidate)
    if (sealed['cohort_sha256'] != cohort['sha256'] or sealed['development_sha256'] != development['sha256']
            or sealed['bundle_sha256'] != runtime.bundle_sha256
            or sealed['reference_bundle_sha256'] != RoutingRuntime(args.reference).bundle_sha256
            or sealed['confirmation_used']):
        raise ValueError('Fresh cohort/configuration changed or confirmation already used')
    # Production identity is captured with the experimental route disabled.
    os.environ.pop('NAILIQ_ROUTING_MANIFEST', None)
    if sealed['production_fingerprint'] != evaluation_fingerprint():
        raise ValueError('Production or inference code changed after locking')
    reference_runtime = RoutingRuntime(args.reference)
    candidate_fingerprint = {p: file_hash(p) for p in runtime.dependencies}
    reference_fingerprint = {p: file_hash(p) for p in reference_runtime.dependencies}
    if (candidate_fingerprint != sealed['candidate_execution_fingerprint']
            or reference_fingerprint != sealed['reference_execution_fingerprint']):
        raise ValueError('Substituted candidate/reference execution manifest')
    dependencies = {**candidate_fingerprint, **reference_fingerprint}
    if any(file_hash(path) != expected for path, expected in dependencies.items()):
        raise ValueError('Candidate/reference display policy changed after locking')
    regression = json.loads(args.regression.read_text())
    device, phone = json.loads(args.device.read_text()), json.loads(args.phone.read_text())
    if (regression.get('non_regression_passed') is not True or device.get('mismatches') != 0
            or phone.get('passes_shown') is not True
            or any(report.get('bundle_sha256') != runtime.bundle_sha256 for report in (regression, device, phone))):
        raise ValueError('Matching regression, device and phone checks must pass before consuming confirmation')
    LEDGER.mkdir(parents=True, exist_ok=True)
    for claim in consumption_paths(cohort):
        with claim.open('x', encoding='utf-8') as ledger:
            json.dump({'cohort_sha256': cohort['sha256'], 'bundle_sha256': runtime.bundle_sha256,
                       'lock_sha256': file_hash(args.lock)}, ledger)
    sealed['confirmation_used'] = True
    args.lock.write_text(json.dumps(sealed, indent=2))
    before = {p: file_hash(p) for p in runtime.dependencies}
    from ml.eval.eval_color_sensitivity import create_eval_client
    _, client = create_eval_client()
    candidate, scopes, errors = evaluate(cohort['rows'], args.candidate, sealed['planned_contexts'], client)
    reference, _, _ = evaluate(cohort['rows'], args.reference, client=client)
    production, _, _ = evaluate(cohort['rows'], None, client=client)
    against_reference, against_production = acceptance(candidate, reference), acceptance(candidate, production)
    groups = subgroup_checks(candidate)
    healthy = sum(r['labels'] == ['healthy'] for r in candidate)
    positives = {c: sum(c in r['labels'] for r in candidate) for c in TARGETS}
    checks = {key: False for key in REQUIRED_CHECKS}
    checks.update({'targets': against_reference['twelve_target_passed'] and healthy >= 400
                       and all(n >= 150 for n in positives.values()),
        'protected_signs': all(against_reference['protected'].values()) and all(against_production['protected'].values()),
        'healthy_scans': against_reference['healthy_scans_preserved'] and against_production['healthy_scans_preserved'],
        'coverage': all(against_reference['coverage'].values()) and all(against_production['coverage'].values()),
        'subgroups': bool(groups) and all(not g['failures'] and g['healthy_n'] for g in groups.values())
                     and not any(key.endswith(':unknown') for key in groups),
        'reviewed': True, 'patient_independent': True, 'blinded': True, 'heldout': True,
        'production_comparison': True,
        'regression': regression.get('non_regression_passed') is True
            and regression.get('bundle_sha256') == runtime.bundle_sha256,
        'device': device.get('mismatches') == 0 and device.get('bundle_sha256') == runtime.bundle_sha256,
        'phone': phone.get('passes_shown') is True and phone.get('bundle_sha256') == runtime.bundle_sha256,
        'endpoint_parity': not errors})
    if (any(file_hash(path) != expected for path, expected in {**before, **dependencies}.items())
            or load_cohort(args.cohort)['sha256'] != cohort['sha256']
            or sealed['production_fingerprint'] != evaluation_fingerprint()):
        raise ValueError('Evidence changed during confirmation')
    eligible = [context_metrics(candidate, scope) for scope in scopes]
    checks['targets'] &= all(entry['positive_patients'] >= 150 and entry['healthy_patients'] >= 400
        and entry['recall'] is not None and entry['recall'] >= .6
        and entry['healthy_fp_rate'] is not None and entry['healthy_fp_rate'] <= .05 for entry in eligible)
    result = {'version': 1, 'phase': 'fresh_confirmation', 'bundle_sha256': runtime.bundle_sha256,
        'cohort_sha256': cohort['sha256'], 'healthy_patients': healthy, 'checks': checks,
        'eligible_contexts': eligible,
        'reference_comparison': against_reference, 'production_comparison': against_production, 'subgroups': groups,
        'replay_mismatches': errors, 'passed': all(checks.values()),
        'limitations': ['No observed regression is not a guarantee of population performance',
            'Prospective display permissions were evaluated in isolation; grants require all gates to pass'],
        'evidence_hashes': {str(p): file_hash(p) for p in (args.lock, args.regression, args.device, args.phone)}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    for name, records in (('candidate', candidate), ('reference', reference), ('production', production)):
        args.out.with_name(args.out.stem + '.' + name + '.json').write_text(json.dumps(records, indent=2))
    print(json.dumps({'passed': result['passed'], 'checks': checks}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('template', 'lock', 'run', 'issue'))
    for name in ('candidate', 'reference', 'cohort', 'development', 'lock', 'regression', 'device', 'phone', 'report', 'context-plan'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    required = {'template': (), 'lock': ('candidate', 'reference', 'cohort', 'development', 'context_plan'),
        'run': ('candidate', 'reference', 'cohort', 'development', 'lock', 'regression', 'device', 'phone'),
        'issue': ('candidate', 'report')}
    for name in required[args.action]:
        if getattr(args, name) is None:
            parser.error('--' + name.replace('_', '-') + ' is required for ' + args.action)
    if args.action == 'template':
        if args.out.exists():
            raise ValueError('Preserve the existing review template')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(template(), indent=2))
    elif args.action == 'lock':
        lock(args)
    elif args.action == 'run':
        run(args)
    else:
        from ml.infer.validation_evidence import report_approves
        report = json.loads(args.report.read_text())
        runtime = RoutingRuntime(args.candidate)
        grants = [entry['context'] for entry in report.get('eligible_contexts', [])]
        if not grants or any(not report_approves(report, grant, runtime.bundle_sha256) for grant in grants):
            raise ValueError('Independent confirmation has not cleared every gate')
        if args.out.exists() and json.loads(args.out.read_text()).get('records'):
            raise ValueError('Preserve previously issued records')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        destination = args.out.parent / (file_hash(args.report) + '.json')
        destination.write_bytes(args.report.read_bytes())
        registry = {'version': 1, 'records': [{'context': grant, 'report_file': destination.name,
                     'report_sha256': file_hash(destination)} for grant in grants]}
        args.out.write_text(json.dumps(registry, indent=2))
        # Changing the manifest revision refreshes the app's cached runtime while
        # keeping the approved semantic bundle independent of evidence paths.
        manifest = json.loads(args.candidate.read_text())
        manifest['validation_evidence'] = str(args.out.resolve())
        manifest['validation_revision_sha256'] = file_hash(args.out)
        args.candidate.write_text(json.dumps(manifest, indent=2))
