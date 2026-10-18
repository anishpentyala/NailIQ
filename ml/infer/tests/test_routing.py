from concurrent.futures import ThreadPoolExecutor

import pytest

from ml.eval.routed_replay import coverage_ok, replay
from ml.infer import color_classifier, color_fusion, routing


def branch(verdict='within', probs=None, failure=None):
    heur = {'label': 'terrys_nails', 'display_name': 'Terry', 'verdict': verdict,
            'value': None, 'unit': None, 'confidence': .5, 'failure_reason': failure}
    return {'heuristics': {'terrys_nails': heur}, 'probs': probs,
            'failure': failure, 'roi_only': False}


def test_concurrent_rules_do_not_contaminate_other_runtimes():
    floors = dict(color_classifier.CLASS_CONFIDENCE_THRESHOLD)
    ovr = dict(color_fusion.OVR_THRESHOLD)
    metadata = {'app_conditions': ['terrys_nails']}
    sample = branch(probs={'healthy': .55, 'terrys_nails': .45})
    def run(threshold):
        return routing.decide('terrys_nails', sample, metadata, [.45, threshold, None])['verdict']
    with ThreadPoolExecutor(4) as pool:
        assert list(pool.map(run, [.3, .8] * 30)) == ['outside', 'within'] * 30
    assert floors == color_classifier.CLASS_CONFIDENCE_THRESHOLD
    assert ovr == color_fusion.OVR_THRESHOLD


def test_fallback_selects_full_legacy_evidence_and_never_a_withholding_gate():
    metadata = {'app_conditions': ['terrys_nails'], 'unvalidated_conditions': ['terrys_nails']}
    samples = {'legacy': branch('outside', {'healthy': .1, 'terrys_nails': .9}),
               'detector': branch(failure='too_blurry')}
    result, key = routing.choose('terrys_nails', samples, metadata, 'detector_fallback')
    assert (result['verdict'], key) == ('outside', 'legacy')
    samples['detector'] = branch('within', {'healthy': .9, 'terrys_nails': .1})
    result, key = routing.choose('terrys_nails', samples, metadata, 'detector_fallback')
    assert (result['verdict'], key) == ('within', 'detector')


def test_invalid_assisted_box_cannot_switch_to_automatic_evidence():
    samples = {'legacy': branch('outside', {'healthy': .1, 'terrys_nails': .9}),
               'assisted': branch(failure='invalid_nail_bbox')}
    result, key = routing.choose('terrys_nails', samples, {'app_conditions': ['terrys_nails']}, 'detector_fallback')
    assert result['verdict'] == 'inconclusive' and key == 'assisted'


def test_missing_model_does_not_assert_the_heuristic():
    assert routing.decide('terrys_nails', branch('outside'), {'app_conditions': ['terrys_nails']})['verdict'] == 'inconclusive'


def test_detector_clubbing_gain_rejected_for_healthy_abstentions():
    baseline = {'healthy': {'n': 311, 'outside': 0, 'inconclusive': 81}}
    detector = {'healthy': {'n': 311, 'outside': 0, 'inconclusive': 104}}
    assert not coverage_ok(detector, baseline)
    assert coverage_ok({'healthy': {'n': 311, 'outside': 0, 'inconclusive': 87}}, baseline)


def test_fallback_cannot_remove_low_sample_disagreement_protection():
    sample = branch('within', {'healthy': .1, 'leukonychia': .9})
    sample['heuristics']['leukonychia'] = {**sample['heuristics'].pop('terrys_nails'), 'label': 'leukonychia'}
    result, key = routing.choose('leukonychia', {'legacy': sample, 'detector': sample},
                                 {'app_conditions': ['leukonychia']}, 'detector_fallback')
    assert result['verdict'] == 'inconclusive'
    assert result['agreement'] == 'low_sample_disagree'


def test_shape_route_preserves_reliable_geometry_and_nulls_failed_measurements():
    original = {'label': 'clubbing', 'verdict': 'within', 'value': 160, 'unit': 'deg'}
    candidate = {'label': 'clubbing', 'verdict': 'outside', 'track_used': 'appearance'}
    assert routing.merge_shape(original, candidate) == original
    failed = {**original, 'verdict': 'inconclusive', 'value': None}
    result = routing.merge_shape(failed, candidate)
    assert result['value'] is None and result['unit'] is None and result['geometry']['value'] is None


def test_mixed_replay_rejects_old_cache_and_missing_evidence():
    with pytest.raises(ValueError, match='version-two'):
        replay({'findings': {}}, 'terrys_nails', {}, {'model': 'base', 'route': 'legacy'})
    with pytest.raises(ValueError, match='Missing required branch'):
        replay({'cache_version': 2, 'branches': {}}, 'terrys_nails', {'base': {}}, {'model': 'base', 'route': 'legacy'})


def test_runtime_metadata_is_immutable_recursively():
    metadata = routing.immutable({'conditions': {'pallor': {'rules': [.45, None, .05]}}})
    with pytest.raises(TypeError):
        metadata['conditions']['pallor']['rules'][0] = .1
