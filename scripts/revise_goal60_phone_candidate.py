"""Restore a known phone-safe route after a failed development phone check."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.withholding_checks import acceptance
from ml.infer.routing import RoutingRuntime, rules_for, digest
from ml.infer.validation_evidence import context, identity
from scripts.select_goal60_withholding import displayed
from scripts.run_goal60_round2 import checked
from scripts.report_goal60 import CONDITIONS


def revise():
    folder = ROOT / 'data/raw/goal60_withholding_round3'
    path = folder / 'selected.json'
    selection_path = path.with_suffix('.selection.json')
    original = json.loads(selection_path.read_text())
    phone_path = ROOT / 'ml/eval/goal60_withholding_selected_phone_cpu.json'
    phone = json.loads(phone_path.read_text())
    if phone['passes_pre_policy'] or not phone['passes_shown']:
        raise ValueError('Expected a pre-policy-only failed phone check')
    failed = {c for r in phone['rows'] for c in r['pre_policy_false_positives']}
    if failed != {'melanonychia'}:
        raise ValueError('Reassess unexpected failed conditions')
    spec = json.loads(path.read_text())
    rejected = folder / 'rejected_phone_candidate'
    rejected.mkdir()
    for source in (path, selection_path, path.with_suffix('.contexts.json'), phone_path):
        (rejected / source.name).write_bytes(source.read_bytes())
    anchor = json.loads((folder / 'development.json').read_text())
    spec['conditions']['melanonychia'] = copy.deepcopy(anchor['conditions']['melanonychia'])
    path.write_text(json.dumps(spec, indent=2))
    runtime = RoutingRuntime(path)
    metadata = {key: model.metadata for key, model in runtime.models.items()}
    records = checked(ROOT / 'ml/eval/goal60_withholding_development_gpu_valid.json', folder / 'development.json')
    reference = json.loads((ROOT / 'ml/eval/goal60_round2_selected_gpu_valid.json').read_text())
    def materialize(permissions):
        rows = []
        for row in records:
            findings = {}
            for c in CONDITIONS:
                verdict, key = displayed(row, c, spec['conditions'][c], metadata, permissions)
                findings[c] = {**row['findings'][c], 'shown': verdict, 'route_id': key}
            rows.append({**row, 'findings': findings})
        return rows
    actual = acceptance(materialize(()), reference, True)
    prospective = acceptance(materialize(original['hypothetical_unlocks']), reference, True)
    if not actual['non_regression_passed'] or not prospective['non_regression_passed']:
        raise ValueError('Restoring the phone route must preserve displayed constraints')
    scopes = {}
    for row in records:
        for c in original['hypothetical_unlocks']:
            finding = runtime.selected(row['branches'], c)
            if finding.get('unvalidated_verdict') not in ('within', 'outside'):
                continue
            cfg = spec['conditions'][c]
            scope = context(runtime, c, cfg, row['branches'][finding['route_id']],
                rules_for(metadata[cfg['model']], c, cfg.get('rules')), runtime.bundle_sha256)
            scopes[identity(scope)] = scope
    path.with_suffix('.contexts.json').write_text(json.dumps({'version': 1,
        'bundle_sha256': runtime.bundle_sha256, 'contexts': list(scopes.values()),
        'scope': 'Development proposal only; no approval'}, indent=2))
    original.update({'phase': 'development_phone_revision', 'manifest_sha256': digest(path),
        'actual_policy': actual, 'prospective': prospective,
        'phone_revision': {'failed_phone_sha256': digest(phone_path),
            'rejected_manifest_sha256': digest(rejected / path.name),
            'condition': 'melanonychia', 'restored_config': spec['conditions']['melanonychia'],
            'reason': 'Raw healthy phone pre-policy false positive; confirmation not used'}})
    selection_path.write_text(json.dumps(original, indent=2))
    cpu = {**spec, 'device': 'cpu'}
    (folder / 'selected_cpu.json').write_text(json.dumps(cpu, indent=2))
    print(json.dumps({'actual': actual['target_count'], 'prospective': prospective['target_count'],
        'actual_healthy_flags': actual['healthy_scans']['any_outside'],
        'prospective_healthy_flags': prospective['healthy_scans']['any_outside']}))


if __name__ == '__main__':
    revise()
