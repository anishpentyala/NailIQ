import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ml.infer import routing, validation_evidence as evidence
from ml.eval.withholding_checks import acceptance, PROTECTED
from ml.eval.confirmation_cohort import load_cohort, separate_cohorts, template
from scripts.select_goal60_withholding import joint_pick
from scripts.report_goal60 import CONDITIONS


def scope():
    return {'condition': 'pallor', 'roi_mode': 'detector', 'evidence_type': 'measured_color', 'context_sha256': 'scope'}


def registry(tmp_path, mutate=None):
    report = {'version': 1, 'phase': 'fresh_confirmation', 'bundle_sha256': 'bundle',
        'cohort_sha256': 'cohort', 'healthy_patients': 400,
        'checks': {key: True for key in evidence.REQUIRED_CHECKS},
        'eligible_contexts': [{'context': scope(), 'positive_patients': 150,
            'healthy_patients': 400, 'recall': .7, 'healthy_fp_rate': .02}]}
    if mutate:
        mutate(report)
    report_path = tmp_path / 'report.json'
    report_path.write_text(json.dumps(report))
    path = tmp_path / 'registry.json'
    path.write_text(json.dumps({'version': 1, 'records': [{'context': scope(),
        'report_file': 'report.json', 'report_sha256': evidence.file_hash(report_path)}]}))
    return evidence.EvidenceRegistry(path, 'bundle'), path, report_path


def test_exact_scope_and_revocation(tmp_path):
    checked, path, _ = registry(tmp_path)
    assert checked.allows(scope())
    for key, value in [('condition', 'leukonychia'), ('roi_mode', 'assisted'),
                       ('evidence_type', 'roi_only_color'), ('context_sha256', 'different')]:
        assert not checked.allows({**scope(), key: value})
    path.write_text(json.dumps({'version': 1, 'records': []}))
    assert not checked.allows(scope())


@pytest.mark.parametrize('mutation', [
    lambda r: r.update(phase='development_selection'),
    lambda r: r['checks'].update(healthy_scans=False),
    lambda r: r['checks'].pop('blinded'),
    lambda r: r.update(bundle_sha256='stale'),
    lambda r: r['eligible_contexts'][0].update(positive_patients=3),
    lambda r: r['eligible_contexts'][0].update(healthy_patients=0),
    lambda r: r['eligible_contexts'][0].update(healthy_fp_rate=.065),
    lambda r: r['eligible_contexts'][0].update(recall=.59),
])
def test_development_or_inadequate_evidence_never_grants(tmp_path, mutation):
    checked, _, _ = registry(tmp_path, mutation)
    assert not checked.allows(scope())
    assert checked.errors


def test_report_tampering_and_missing_registry(tmp_path):
    checked, _, report = registry(tmp_path)
    report.write_text('{}')
    assert not checked.allows(scope())
    assert not evidence.EvidenceRegistry(tmp_path / 'missing.json', 'bundle').allows(scope())


def test_semantic_identity_is_portable_but_rule_sensitive(monkeypatch):
    monkeypatch.setattr(evidence, 'code_identity', lambda: 'code')
    meta = {'classes': ['healthy', 'pallor'], 'app_conditions': ['pallor']}
    model = SimpleNamespace(metadata=meta, dependencies={'/one/model.json': 'meta', '/one/model.pt': 'weights'})
    runtime = SimpleNamespace(spec={'conditions': {'pallor': {'model': 'p', 'route': 'detector_fallback'}}},
                              models={'p': model}, locator=None)
    first = evidence.bundle_identity(runtime)
    model.dependencies = {'/relocated/model.json': 'meta', '/relocated/model.pt': 'weights'}
    assert evidence.bundle_identity(runtime) == first
    branch = {'mode': 'detector', 'roi_only': False}
    config = runtime.spec['conditions']['pallor']
    original = evidence.context(runtime, 'pallor', config, branch, routing.rules_for(meta, 'pallor'))
    changed = evidence.context(runtime, 'pallor', config, branch, routing.rules_for(meta, 'pallor', [.7, None, .05]))
    assert original != changed
    assert original != evidence.context(runtime, 'pallor', config, {**branch, 'roi_only': True}, routing.rules_for(meta, 'pallor'))
    model.dependencies['/relocated/model.pt'] = 'new_weights'
    assert evidence.bundle_identity(runtime) != first


def test_scope_never_rescues_low_sample_or_branch_failure():
    heur = {'label': 'leukonychia', 'display_name': 'Leukonychia', 'value': None,
            'unit': None, 'verdict': 'within', 'confidence': .5}
    sample = {'mode': 'detector', 'heuristics': {'leukonychia': heur},
              'probs': {'healthy': .1, 'leukonychia': .9}, 'roi_only': False}
    metadata = {'app_conditions': ['leukonychia']}
    assert routing.decide('leukonychia', sample, metadata)['verdict'] == 'inconclusive'
    sample['failure'] = 'too_blurry'
    assert routing.decide('leukonychia', sample, metadata)['failure_reason'] == 'too_blurry'


def record(path, labels, outside=()):
    return {'path': path, 'labels': labels, 'findings': {c: {'shown': 'outside' if c in outside else 'within',
        'route_id': 'legacy', 'evidence_type': None} for c in CONDITIONS}}


def test_joint_false_alarm_limit_catches_individually_passing_changes():
    reference = [record(str(i), ['healthy']) for i in range(100)]
    candidate = copy.deepcopy(reference)
    for i in range(3):
        candidate[i]['findings']['pallor']['shown'] = 'outside'
        candidate[i+3]['findings']['terrys_nails']['shown'] = 'outside'
    result = acceptance(candidate, reference)
    assert result['candidate']['pallor']['fp_rate'] == .03
    assert result['candidate']['terrys_nails']['fp_rate'] == .03
    assert result['healthy_scans']['any_outside'] == 6
    assert not result['healthy_scans_preserved']
    assert not result['non_regression_passed']


def test_withheld_and_missing_positives_are_misses_and_coverage_cannot_trade():
    reference = [record('h', ['healthy']), record('p', ['pallor'], ['pallor'])]
    candidate = copy.deepcopy(reference)
    candidate[1]['findings'].pop('pallor')
    candidate[0]['findings']['pitting']['shown'] = 'inconclusive'
    result = acceptance(candidate, reference)
    assert result['candidate']['pallor']['recall'] == 0
    assert not result['coverage']['pallor']
    assert not result['coverage']['pitting']
    assert not result['non_regression_passed']


def test_exact_protected_routes_and_verdicts():
    reference = [record('h', ['healthy'])]
    candidate = copy.deepcopy(reference)
    candidate[0]['findings'][PROTECTED[0]]['route_id'] = 'detector'
    assert not acceptance(candidate, reference, True)['protected'][PROTECTED[0]]


def test_joint_selector_finds_shared_error_solution():
    def option(mask, recall):
        return {'healthy_mask': mask, 'rank': (1, recall, 10, 0)}
    picks, flags = joint_pick({'a': [option(1, .9), option(2, .8)], 'b': [option(2, .9)]}, 1)
    assert flags == 1 and picks['a']['healthy_mask'] == 2


def cohort_file(tmp_path, role='confirmation', group='patient1'):
    doc = template()
    doc.update(role=role, blinded_review=True, patient_independence_confirmed=True,
               reviewers={'r': {'qualification': 'unit-test reviewer'}})
    (tmp_path / 'side.bin').write_bytes(b'bad-side-photo')
    (tmp_path / 'top.bin').write_bytes(b'bad-top-photo')
    doc['patients'] = [{'patient_group': group, 'primary_capture_index': 1,
        'side_path': 'side.bin', 'top_path': 'top.bin', 'source': 'unit-test', 'skin_tone_band': 'unknown',
        'rights_reference': 'test fixture', 'photo_adequacy': 'inadequate',
        'signs': {c: {'status': 'present' if c == 'pallor' else 'absent', 'reviewer': 'r'} for c in CONDITIONS}}]
    path = tmp_path / 'cohort.json'
    path.write_text(json.dumps(doc))
    return path, doc


def test_reviewed_bad_photos_remain_known_positive(tmp_path):
    path, _ = cohort_file(tmp_path)
    loaded = load_cohort(path)
    assert len(loaded['rows']) == 1 and loaded['rows'][0]['labels'] == ['pallor']


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(patients=[]),
    lambda d: d.update(blinded_review=False),
    lambda d: d['patients'].append(copy.deepcopy(d['patients'][0])),
    lambda d: d['patients'][0]['signs'].pop('pitting'),
    lambda d: d['patients'][0].update(primary_capture_index=2),
    lambda d: d['patients'][0]['signs']['pallor'].update(status='not_assessed'),
])
def test_unreviewed_or_cherry_picked_cohort_rejected(tmp_path, mutation):
    path, doc = cohort_file(tmp_path)
    mutation(doc)
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        load_cohort(path)


def test_development_confirmation_overlap_rejected(tmp_path):
    path, _ = cohort_file(tmp_path)
    confirmation = load_cohort(path)
    development = copy.deepcopy(confirmation)
    development['document']['role'] = 'development'
    with pytest.raises(ValueError, match='overlap'):
        separate_cohorts(development, confirmation)


def test_unused_planned_context_reports_zero_support():
    from scripts.evaluate_goal60_confirmation import context_metrics
    result = context_metrics([], scope())
    assert result['positive_patients'] == result['healthy_patients'] == 0
    assert result['recall'] is None and result['healthy_fp_rate'] is None


def test_consumption_identity_survives_label_edits_and_new_patient_photo(tmp_path, monkeypatch):
    from scripts import evaluate_goal60_confirmation as confirmation
    monkeypatch.setattr(confirmation, 'LEDGER', tmp_path / 'ledger')
    path, _ = cohort_file(tmp_path)
    cohort = load_cohort(path)
    old_claims = set(confirmation.consumption_paths(cohort))
    cohort['rows'][0]['labels'] = ['healthy']
    cohort['rows'][0]['photos']['top']['sha256'] = 'replacement'
    new_claims = set(confirmation.consumption_paths(cohort))
    assert any(p.name.startswith('patient-') for p in old_claims & new_claims)


def test_zero_discordance_does_not_claim_zero_population_uncertainty():
    records = [record('h', ['healthy'])]
    interval = acceptance(records, records)['paired_healthy']['approximate_ci95']
    assert interval[0] < 0 < interval[1]


@pytest.mark.parametrize('payload', [[], {'version': 1, 'records': [None]}, {'version': 1, 'records': [{}]}])
def test_malformed_registry_fails_closed(tmp_path, payload):
    path = tmp_path / 'malformed.json'
    path.write_text(json.dumps(payload))
    checked = evidence.EvidenceRegistry(path, 'bundle')
    assert checked.errors and not checked.allows(scope())


def test_detector_implementation_is_in_grant_identity(monkeypatch):
    monkeypatch.setattr(evidence, 'file_hash', lambda _: 'old')
    before = evidence.code_identity()
    monkeypatch.setattr(evidence, 'file_hash', lambda p: 'new' if Path(p).name == 'nail_detection_model.py' else 'old')
    assert evidence.code_identity() != before


def test_scope_clears_only_policy_and_never_branch_failure(tmp_path, monkeypatch):
    checked, _, _ = registry(tmp_path)
    runtime = routing.RoutingRuntime.__new__(routing.RoutingRuntime)
    config = {'model': 'baseline', 'route': 'detector_fallback'}
    runtime.spec = {'conditions': {'pallor': config}}
    runtime.bundle_sha256 = 'bundle'
    runtime.validation = checked
    runtime.models = {'baseline': SimpleNamespace(metadata={'app_conditions': ['pallor']})}
    monkeypatch.setattr(evidence, 'context', lambda *a: {**scope(), 'roi_mode': a[3]['mode']})
    heur = {'label': 'pallor', 'display_name': 'Pallor', 'value': None, 'unit': None,
            'verdict': 'outside', 'confidence': .5, 'failure_reason': None}
    sample = {'mode': 'detector', 'bbox': None, 'skin_ita': None, 'roi_only': False,
        'heuristics': {'pallor': heur}, 'models': {'baseline': {'probs': {'healthy': .1, 'pallor': .9}}}}
    branches = {'detector': sample, 'legacy': {**sample, 'mode': 'legacy'}}
    assert runtime.selected(branches, 'pallor')['verdict'] == 'outside'
    runtime.validation = evidence.EvidenceRegistry(None, 'bundle')
    assert runtime.selected(branches, 'pallor')['verdict'] == 'inconclusive'
    runtime.validation = checked
    branches['detector'] = {**sample, 'failure': 'too_blurry'}
    # The detector grant does not cover the selected legacy fallback.
    assert runtime.selected(branches, 'pallor')['verdict'] == 'inconclusive'


def test_endpoint_failure_retains_reviewed_positive(tmp_path):
    from scripts.evaluate_goal60_confirmation import evaluate
    path, _ = cohort_file(tmp_path)
    client = SimpleNamespace(post=lambda *a, **k: SimpleNamespace(status_code=400))
    records, _, _ = evaluate(load_cohort(path)['rows'], None, client=client)
    assert records[0]['labels'] == ['pallor']
    assert all(f['shown'] == 'inconclusive' for f in records[0]['findings'].values())


def test_geometry_replay_preserves_premerge_authority():
    from ml.eval.routed_replay import replay
    original = {'label': 'clubbing', 'verdict': 'within', 'value': 160, 'unit': 'deg'}
    image = {'cache_version': 2, 'geometry_evidence': {'clubbing': original},
        'branches': {'legacy': {'mode': 'legacy', 'heuristics': {'clubbing': original},
            'models': {'baseline': {'probs': {'healthy': .1, 'clubbing': .9}}}}}}
    verdict, key = replay(image, 'clubbing', {'baseline': {}}, {'model': 'baseline', 'route': 'legacy'})
    assert verdict == 'within' and key is None


def test_joint_display_handles_geometry_passthrough_without_roi_key():
    from scripts.select_goal60_withholding import displayed
    original = {'label': 'clubbing', 'verdict': 'inconclusive', 'value': None, 'unit': None}
    image = {'cache_version': 2, 'geometry_evidence': {'clubbing': original},
        'branches': {'legacy': {'mode': 'legacy', 'heuristics': {'clubbing': original},
            'models': {'baseline': {'probs': {'healthy': .3, 'clubbing': .3}}}}}}
    verdict, key = displayed(image, 'clubbing', {'model': 'baseline', 'route': 'legacy'}, {'baseline': {}}, ())
    assert verdict == 'inconclusive' and key is None


def test_specialist_cannot_train_from_confirmation(tmp_path):
    from scripts.build_goal60_reviewed_specialist import build
    path, _ = cohort_file(tmp_path)
    output = tmp_path / 'training'
    with pytest.raises(ValueError, match='confirmation'):
        build(path, 'pallor', output)
    assert not output.exists()


def test_specialist_requires_explicit_patient_split(tmp_path):
    from scripts.build_goal60_reviewed_specialist import build
    path, _ = cohort_file(tmp_path, role='development')
    with pytest.raises(ValueError, match='Preassign'):
        build(path, 'pallor', tmp_path / 'training')


def test_joint_selection_can_retain_withholding_when_unlock_exceeds_budget():
    from scripts.select_goal60_withholding import permission_options, joint_pick
    assert permission_options('pallor', ('pallor',)) == ((), ('pallor',))
    assert permission_options('pitting', ('pallor',)) == ((),)
    tables = {
        'pitting': [{'healthy_mask': 1, 'rank': (1, .8, 1, 0)}],
        'pallor': [
            {'healthy_mask': 2, 'rank': (1, .7, 1, -1), 'proposed_permission': True},
            {'healthy_mask': 0, 'rank': (0, 0., 0, 0), 'proposed_permission': False},
        ],
    }
    picks, flags = joint_pick(tables, 1)
    assert flags == 1 and picks['pallor']['proposed_permission'] is False


def test_device_clone_preserves_scoped_approval_across_directories(tmp_path):
    from scripts.check_goal60_device_parity import cpu_spec
    checked, _, _ = registry(tmp_path)
    spec = {'models': {'baseline': 'models'}, 'validation_evidence': checked.path.name}
    clone = cpu_spec(spec, tmp_path)
    moved = tmp_path / 'elsewhere'
    moved.mkdir()
    loaded = evidence.EvidenceRegistry(moved / clone['validation_evidence'], 'bundle')
    assert loaded.allows(scope()) and not loaded.errors
