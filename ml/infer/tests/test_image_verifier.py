import math
import pytest

from ml.eval.image_verifier import shadow, threshold, verifier_score, runtime_reference
from scripts.prepare_goal60_image_verifiers import grouped_roles


def test_positive_verifier_needs_first_stage_support_and_preserves_reference():
    for reference in ('within', 'outside', 'inconclusive'):
        for unsupported in ('within', 'inconclusive', None):
            result = shadow(reference, unsupported, .99, .8)
            assert result['actual_shown'] == result['hypothetical_shown'] == reference
        assert shadow(reference, 'outside', .7, .8)['hypothetical_shown'] == reference
        assert shadow(reference, 'outside', .9, .8)['actual_shown'] == reference
        assert shadow(reference, 'outside', .9, .8)['hypothetical_shown'] == 'outside'
        assert not shadow(reference, 'outside', .9, .8)['clinical_release_eligible']


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), -1., 1.1])
def test_unavailable_or_invalid_probability_never_adds_a_positive(value):
    assert shadow('within', 'outside', value, .8)['hypothetical_shown'] == 'within'


def test_calibration_boundary_has_zero_additional_negative_flags():
    rows = [{'labels': ['healthy'], 'stage1': 'outside', 'probability': .9},
            {'labels': ['healthy'], 'stage1': 'within', 'probability': .99}]
    cutoff = threshold(rows)
    assert cutoff > .9
    assert not shadow('inconclusive', 'outside', .9, cutoff)['added_positive']
    rows[0]['probability'] = 1.
    assert threshold(rows) > 1.
    with pytest.raises(ValueError, match='target-negative'):
        threshold([])


def test_failed_localization_cannot_be_overruled_by_verifier():
    class ForbiddenModel:
        def predict(self, *args):
            raise AssertionError('Model must not run without validated crop')
    for reason in ('invalid_image', 'too_blurry', 'too_much_glare', 'nail_region_unclear'):
        assert verifier_score('', {'legacy': {'bbox': [0, 0, 1, 1], 'failure': reason}}, ForbiddenModel(), 'pallor') == (None, reason)


def test_transitive_patient_original_and_crop_links_share_one_role():
    rows = [{'path': str(i), 'group': g, 'sha256': h, 'split': 'train'}
            for i, (g, h) in enumerate([('a', 'x'), ('b', 'x'), ('b', 'y'), ('c', 'z')])]
    roles = grouped_roles(rows, {'2': 'crop', '3': 'crop'})
    assert len(set(roles.values())) == 1
    rows[-1]['split'] = 'valid'
    assert set(grouped_roles(rows, {'2': 'crop', '3': 'crop'}).values()) == {'quarantine'}


def test_bounded_calibration_is_finite_and_handles_tta():
    torch = pytest.importorskip('torch')
    from ml.train.train_color_classifier import fit_color_temperature
    logits = torch.tensor([[1., -1.], [-1., 1.]])
    # Intentionally inverted logits made unbounded optimization diverge previously.
    targets = torch.tensor([1, 0])
    temperature = fit_color_temperature(logits, targets)
    assert math.isfinite(temperature) and .049 <= temperature <= 100.01
    assert math.isfinite(fit_color_temperature(torch.stack((logits, logits), 1), targets))
    with pytest.raises(ValueError, match='Finite'):
        fit_color_temperature(logits * float('nan'), targets)


def test_cpu_comparison_cannot_silently_switch_models(tmp_path):
    import json
    reference = tmp_path / 'selected.json'
    cpu = tmp_path / 'selected_cpu.json'
    reference.write_text(json.dumps({'device': 'cuda:0', 'models': {'a': 'frozen'}}))
    cpu.write_text(json.dumps({'device': 'cpu', 'models': {'a': 'frozen'}}))
    assert runtime_reference(reference, 'cpu') == cpu
    cpu.write_text(json.dumps({'device': 'cpu', 'models': {'a': 'different'}}))
    with pytest.raises(ValueError, match='changes more'):
        runtime_reference(reference, 'cpu')
