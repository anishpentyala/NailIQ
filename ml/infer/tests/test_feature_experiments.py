"""Guard the research experiment against false validation and split leakage."""
import numpy as np
import pytest
import cv2

from ml.eval.sign_features import describe, normalized, forest_score
from scripts.run_goal60_feature_experiments import fold_rows, metric, fit
from scripts.check_goal60_feature_display import shown


def region(grid):
    return {'S': np.full(100, .1), 'V': grid.ravel(), 'lab_a': np.full(100, 5.),
            'lab_b': np.full(100, 8.), 'skin_lab_a': 12., 'skin_lab_b': 10.,
            'glare_frac': 0., 'grid_v': grid, 'grid_s': np.full(grid.shape, .1)}


def test_distal_pattern_is_invariant_to_uniform_brightness_offset():
    grid = np.full((64, 48), .85)
    grid[-8:] = .55
    names, a = describe(region(grid))
    _, b = describe(region(grid - .12))
    for i, name in enumerate(names):
        if 'relative_value' in name or 'contrast' in name:
            assert a[i] == pytest.approx(b[i])
    assert a[names.index('proximal_distal_contrast_7')] > 0


def test_missing_skin_does_not_become_a_measured_normal_value():
    r = region(np.full((64, 48), .8))
    r['skin_lab_a'] = r['skin_lab_b'] = None
    names, values = describe(r)
    x, _, _ = normalized([values, values])
    column = names.index('lab_a_skin_difference')
    assert np.isnan(values[column])
    assert np.isfinite(x).all()
    assert x[0, len(names) + column] == 1


def test_exact_copy_links_groups_and_valid_overlap_quarantines_train():
    rows = [{'path': 'a', 'split': 'train', 'group': 'patient-a', 'sha256': 'copy'},
            {'path': 'b', 'split': 'train', 'group': 'patient-b', 'sha256': 'copy'},
            {'path': 'c', 'split': 'valid', 'group': 'patient-b', 'sha256': 'third'},
            {'path': 'd', 'split': 'train', 'group': 'patient-d', 'sha256': 'fourth'}]
    train, calibration, quarantined = fold_rows(rows)
    assert {r['path'] for r in quarantined} == {'a', 'b'}
    assert {r['path'] for r in train + calibration} == {'d'}


def test_positive_failures_count_as_misses_and_healthy_abstention_is_separate():
    rows = [{'path': 'a', 'labels': ['pallor']}, {'path': 'b', 'labels': ['pallor']},
            {'path': 'c', 'labels': ['healthy']}, {'path': 'd', 'labels': ['healthy']}]
    result = metric(rows, {'a': 'outside', 'b': 'inconclusive', 'c': 'outside', 'd': 'inconclusive'}, 'pallor')
    assert result['recall'] == .5
    assert result['fp_rate'] == .5
    assert result['healthy_correct'] == 0
    assert result['positive_inconclusive'] == result['healthy_inconclusive'] == 1


def test_scored_experiment_cannot_be_refit(tmp_path):
    (tmp_path / 'results.json').write_text('{}')
    with pytest.raises(ValueError, match='cannot be overwritten'):
        fit(tmp_path)


def test_forest_votes_select_positive_class_on_known_answer_data():
    cv2.setRNGSeed(42)
    x = np.array([[-2.], [-1.], [1.], [2.]] * 20, np.float32)
    y = np.array([0, 0, 1, 1] * 20, np.int32)
    model = cv2.ml.RTrees_create()
    model.setMaxDepth(4)
    model.setMinSampleCount(4)
    model.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER, 32, 0))
    assert model.train(x, cv2.ml.ROW_SAMPLE, y)
    scores = forest_score(model, np.array([[-1.5], [1.5]], np.float32))
    assert scores[0] < .1 and scores[1] > .9


def test_hidden_prediction_never_counts_as_displayed_success():
    assert shown({'findings': {'pallor': {'verdict': 'outside', 'shown': 'inconclusive'}}}, 'pallor') == 'inconclusive'
    with pytest.raises(ValueError, match='Actual shown verdict'):
        shown({'findings': {'pallor': {'verdict': 'outside'}}}, 'pallor')
