import pytest

from scripts.freeze_goal60_candidate import candidate_manifest


def test_freezing_an_experiment_cannot_inherit_deployment_approval():
    source = {'deployment_approved': True, 'validated_roi_modes': ['assisted', 'detector'],
              'validated_appearance_conditions': ['clubbing'], 'classes': ['healthy', 'clubbing'],
              'unvalidated_conditions': ['pitting']}
    rules = {'min_recall': 0.6, 'max_fp': 0.05, 'unvalidated': ['clubbing'],
             'rules': {'clubbing': [0.2, None, None], 'pitting': [0.45, 0.15, 0.05]}}
    result = candidate_manifest(source, rules, {'test_evaluated': False})
    assert not result['deployment_approved']
    assert result['validated_roi_modes'] == result['validated_appearance_conditions'] == []
    assert 'clubbing' in result['unvalidated_conditions']
    assert 'pitting' in result['unvalidated_conditions']
    assert result['decision_rules'] == {'pitting': [0.45, 0.15, 0.05]}
    assert result['appearance_rules']['clubbing']['floor'] == 0.2
    assert source['deployment_approved']


@pytest.mark.parametrize('minimum,maximum', [(0.59, 0.05), (0.6, 0.051), (0.6, -0.01)])
def test_candidate_freeze_rejects_weaker_success_criteria(minimum, maximum):
    with pytest.raises(ValueError):
        candidate_manifest({}, {'min_recall': minimum, 'max_fp': maximum}, {})


def test_selection_counts_every_sign_and_penalizes_healthy_abstentions(monkeypatch):
    from scripts import compare_goal60_candidates as comparison
    monkeypatch.setattr(comparison.tuner, 'replay', lambda r, c: r['findings'].get(c, {}).get('verdict'))
    rows, rank = comparison.summarize([
        {'labels': ['pitting'], 'findings': {'pitting': {'verdict': 'outside'}}},
        {'labels': ['pitting'], 'findings': {}},
        {'labels': ['healthy'], 'findings': {'pitting': {'verdict': 'within'}}},
        {'labels': ['healthy'], 'findings': {}},
    ])
    assert len(rows) == 14
    assert rows['pitting']['recall'] == rows['pitting']['healthy_correct_rate'] == 0.5
    assert rows['pitting']['pos']['inconclusive'] == 1
    assert rank == [0, 0.5 / 14, 0.5 / 14]


def test_healthy_scan_summary_cannot_treat_abstention_as_correct():
    from scripts.report_goal60 import CONDITIONS, healthy_summary
    findings = {c: {'verdict': 'within', 'shown': 'within'} for c in CONDITIONS}
    findings['pitting'] = {'verdict': 'outside', 'shown': 'inconclusive'}
    records = [{'labels': ['healthy'], 'findings': findings}, {'labels': ['healthy'], 'findings': {}}]
    before, shown = healthy_summary(records), healthy_summary(records, True)
    assert before['any_outside_rate'] == 0.5
    assert shown['any_outside_rate'] == 0
    assert before['all_within'] == shown['all_within'] == 0
    assert shown['any_inconclusive'] == 2


def test_fingerprint_path_normalization_does_not_accept_changed_content(monkeypatch, tmp_path):
    from scripts.goal60_evidence import REPO, same_fingerprint
    relative = 'ml/eval/eval_end_to_end.py'
    absolute = str(REPO / relative)
    monkeypatch.chdir(tmp_path)
    assert same_fingerprint({relative: 'original'}, {absolute: 'original'})
    assert not same_fingerprint({relative: 'original'}, {absolute: 'changed'})


def test_selection_does_not_invent_a_missing_cnn_only_finding(monkeypatch):
    from scripts import compare_goal60_candidates as comparison
    monkeypatch.setattr(comparison.tuner, '_RUN_COVERAGE', frozenset({'onychogryphosis'}))
    rows, _ = comparison.summarize([{'labels': ['onychogryphosis'], 'findings': {},
                                    'probs': {'onychogryphosis': 0.99, 'healthy': 0.01}}])
    assert rows['onychogryphosis']['pos']['outside'] == 0
    assert rows['onychogryphosis']['pos']['inconclusive'] == 1
