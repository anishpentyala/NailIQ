import base64

import cv2
import numpy as np
import pytest

from ml.infer import appearance, color_classifier, color_fusion, nail_locator, nail_region, pipeline, validation_policy


@pytest.mark.parametrize('contents', ['{broken', '[]', '{"weights_file": null}'])
def test_optional_locator_handles_invalid_metadata(tmp_path, monkeypatch, contents):
    (tmp_path / 'nail_locator.json').write_text(contents)
    monkeypatch.setattr(nail_locator, '_MODELS', tmp_path)
    assert nail_locator.detect(np.zeros((100, 100, 3), dtype=np.uint8)) == []


def test_side_retake_can_advance_only_with_validated_appearance(monkeypatch):
    calls = []
    def extract(_, require_keypoints):
        calls.append(require_keypoints)
        return None, None, 'keypoints_unclear' if require_keypoints else None
    monkeypatch.setattr(pipeline, '_extract', extract)
    monkeypatch.setattr(color_classifier, 'model_metadata', lambda: {})
    assert pipeline.validate_photo('test') == (False, 'keypoints_unclear')
    assert calls == [True]
    calls.clear()
    monkeypatch.setattr(color_classifier, 'model_metadata', lambda: {'validated_appearance_conditions': ['clubbing']})
    assert pipeline.validate_photo('test') == (True, None)
    assert calls == [True, False]


@pytest.mark.parametrize('box', [None, [], [0, 0, 1], [True, 0, 1, 1],
    [0, 0, float('nan'), 1], [0, 0, float('inf'), 1], [-0.1, 0, 1, 1],
    [0, 0, 1.1, 1], [0.5, 0, 0.5, 1], [0.8, 0, 0.2, 1]])
def test_box_validation_rejects_invalid_coordinates(box):
    assert not nail_locator.valid_bbox(box)


def test_user_box_does_not_bypass_blank_photo():
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    _, encoded = cv2.imencode('.jpg', image)
    ok, reason = pipeline.validate_photo(base64.b64encode(encoded).decode(), False, [0.1, 0.1, 0.9, 0.9])
    assert not ok
    assert reason == 'camera_feed_blank'


def test_roi_focus_uses_the_classifiers_boundary_context_without_lowering_the_floor():
    image = np.full((200, 200, 3), 100, dtype=np.uint8)
    values = (170 + 10 * np.sin(np.arange(80) * np.pi / 20)).astype(np.uint8)
    image[60:140, 60:140] = values[None, :, None]
    box = [0.3, 0.3, 0.7, 0.7]
    assert pipeline.focus_score(image[60:140, 60:140]) < pipeline.BLUR_THRESHOLD
    assert nail_locator.roi_quality(image, box) is None
    blurred = cv2.GaussianBlur(image, (0, 0), 3)
    assert nail_locator.roi_quality(blurred, box) == 'too_blurry'


def test_new_roi_mode_needs_its_own_validation(monkeypatch):
    monkeypatch.setattr(color_classifier, 'model_metadata', lambda: {})
    finding = {'label': 'pitting', 'verdict': 'outside', 'confidence': 0.9}
    assert validation_policy.apply([finding])[0]['verdict'] == 'outside'
    result = validation_policy.apply([finding], 'assisted')[0]
    assert result['verdict'] == 'inconclusive'
    assert result['unvalidated_verdict'] == 'outside'


def test_appearance_fallback_never_invents_a_measurement(monkeypatch):
    metadata = {'appearance_conditions': ['clubbing']}
    monkeypatch.setattr(color_classifier, 'model_metadata', lambda: metadata)
    original = {'label': 'clubbing', 'value': None, 'unit': 'deg', 'verdict': 'inconclusive',
                'failure_reason': 'measurement_unstable', 'confidence': 0}
    prediction = {'predicted_label': 'clubbing', 'probs': {'clubbing': 0.8, 'healthy': 0.2}}
    result = appearance.fallback([original], prediction, 'assisted')[0]
    assert result['track_used'] == 'appearance'
    assert result['verdict'] == 'inconclusive'
    assert result['unvalidated_verdict'] == 'outside'
    assert result['value'] is None and result['unit'] is None
    metadata.update(validated_appearance_conditions=['clubbing'], validated_roi_modes=['assisted'])
    result = appearance.fallback([original], prediction, 'assisted')[0]
    assert result['verdict'] == 'outside'
    assert result['value'] is None and result['geometry']['value'] is None


def test_appearance_never_overrules_valid_geometry(monkeypatch):
    monkeypatch.setattr(color_classifier, 'model_metadata', lambda: {'appearance_conditions': ['clubbing']})
    original = {'label': 'clubbing', 'value': 160, 'verdict': 'inconclusive',
                'geometry': {'value': 160, 'verdict': 'within'}}
    assert appearance.fallback([original], {'probs': {'clubbing': 0.99}}, 'legacy') == [original]


def test_low_floor_appearance_cannot_overrule_a_stronger_healthy_vote(monkeypatch):
    monkeypatch.setitem(color_classifier.CLASS_CONFIDENCE_THRESHOLD, 'clubbing', 0.1)
    assert appearance.signal('clubbing', {'clubbing': 0.15, 'healthy': 0.8})[0] == 'within'


def test_tuner_can_recover_low_support_appearance_only_when_geometry_failed(monkeypatch):
    from ml.eval import tune_color_decision as tuner
    monkeypatch.setattr(tuner, '_RUN_COVERAGE', frozenset({'clubbing'}))
    monkeypatch.setattr(tuner, '_RUN_SHAPE_ELIGIBLE', False)
    monkeypatch.setitem(color_classifier.CLASS_CONFIDENCE_THRESHOLD, 'clubbing', 0.2)
    record = {'findings': {}, 'probs': {'clubbing': 0.3, 'healthy': 0.1, 'pitting': 0.6}}
    assert tuner.replay(record, 'clubbing') == 'inconclusive'
    record['appearance_eligible'] = {'clubbing': True}
    assert tuner.replay(record, 'clubbing') == 'outside'


def test_roi_ai_preserves_low_sample_guard():
    prediction = {'predicted_label': 'leukonychia', 'confidence': 0.95,
                  'probs': {'leukonychia': 0.95, 'healthy': 0.05}}
    finding = {'label': 'leukonychia', 'verdict': 'inconclusive', 'failure_reason': 'nail_region_unclear'}
    result = color_fusion.fuse_roi([finding], prediction, ['leukonychia'])[0]
    assert result['verdict'] == 'inconclusive'
    assert result['failure_reason'] == 'insufficient_data_for_confident_call'


def test_located_roi_can_be_classified_without_silhouette(monkeypatch):
    stripes = np.tile(np.array([80, 160], dtype=np.uint8), (100, 50))
    image = cv2.cvtColor(stripes, cv2.COLOR_GRAY2BGR)
    monkeypatch.setattr(pipeline, 'decode_base64_image', lambda _: image)
    monkeypatch.setattr(pipeline, 'extract_best_contour', lambda _: (None, {'is_valid': False, 'reason': 'no_contour'}))
    monkeypatch.setattr(color_classifier, 'is_available', lambda: True)
    monkeypatch.setattr(color_classifier, 'model_metadata', lambda: {'validated_roi_modes': ['assisted']})
    monkeypatch.setattr(color_classifier, 'app_conditions', lambda: ['pitting'])
    monkeypatch.setattr(color_classifier, 'predict_from_region', lambda *_: {
        'predicted_label': 'pitting', 'confidence': 0.95, 'probs': {'pitting': 0.95, 'healthy': 0.05}})
    findings, overlay, _ = pipeline.analyze_top_color('test', [0.1, 0.1, 0.9, 0.9])
    pitting = next(f for f in findings if f['label'] == 'pitting')
    assert pitting['verdict'] == 'outside'
    assert pitting['value'] is None
    assert overlay['top_bbox_norm'] == [0.1, 0.1, 0.9, 0.9]


def test_selected_box_drives_color_pixels_and_skin_reference():
    image = np.full((240, 160, 3), [90, 110, 150], dtype=np.uint8)
    # Two distinct nail patches on a long finger; select the upper one.
    image[30:90, 50:110] = [110, 140, 155]
    image[100:150, 50:110] = [60, 80, 100]
    contour = np.array([[[30, 10]], [[130, 10]], [[130, 230]], [[30, 230]]], dtype=np.int32)
    region, reason = nail_region.compute_nail_region(image, contour, [50/160, 30/240, 110/160, 90/240])
    assert reason is None
    assert region['region_px'] == 60 * 60
    assert region['region_source'] == 'selected_bbox'
    assert region['bbox'] == (50, 30, 109, 89)
    assert region['skin_lab_a'] is not None
    assert np.nanmax(region['grid_v']) - np.nanmin(region['grid_v']) < 1e-6
