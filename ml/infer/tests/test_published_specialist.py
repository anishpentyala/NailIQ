import json
import numpy as np
import pytest

from ml.infer.tests.test_published_sign_cohort import cohort, write
from scripts import build_goal60_published_specialist as builder
from scripts.evaluate_published_sign_verifier import assessed_metrics
from scripts.evaluate_goal60_image_verifiers import development_records
from scripts.build_goal60_reviewed_specialist import reviewed_crop


def test_partial_crop_builder_keeps_unknown_failed_and_holdout_records(tmp_path, monkeypatch):
    doc = cohort(tmp_path)
    doc['role'] = 'development'
    doc['records'] = []
    for i, (split, status) in enumerate([('train', 'present'), ('train', 'absent'),
                                       ('valid', 'present'), ('valid', 'absent'),
                                       ('valid', 'present'), ('holdout', 'present'), ('valid', None)]):
        name = f'{i}.png'
        (tmp_path / name).write_bytes(str(i).encode())
        doc['records'].append({'source': 'study', 'patient_group': f'p{i}', 'image_path': name,
            'view': 'top', 'development_split': split,
            'signs': {('terrys_nails' if status else 'pitting'): {'status': status or 'indeterminate',
                'reviewer': 'r1', 'original_label_reference': 'original:' + str(i)}}})
    def crop(path):
        if path.stem == '4':
            return None, 'too_blurry'
        if path.stem == '5':
            raise AssertionError('Holdout image must not enter crop building')
        return np.full((32, 32, 3), 127, np.uint8), None
    monkeypatch.setattr(builder, 'reviewed_crop', crop)
    result = builder.build(write(tmp_path, doc), 'terrys_nails', tmp_path / 'crops')
    assert len(result['rows']) == 4
    assert len(result['evaluation_records']) == 7
    assert {r['reason'] for r in result['failures']} == {'too_blurry', 'reserved_holdout', 'unknown_label'}
    assert not any(r['verified_all_signs_absent'] for r in result['rows'])


def test_confirmation_cannot_be_used_for_published_training(tmp_path):
    doc = cohort(tmp_path)
    doc['role'] = 'holdout'
    with pytest.raises(ValueError, match='Only development'):
        builder.build(write(tmp_path, doc), 'terrys_nails', tmp_path / 'crops')


def test_partial_metrics_do_not_drop_failed_positives_or_invent_negatives():
    rows = [{'signs': {'pallor': {'status': status}}, 'actual': {'pallor': call}}
            for status, call in [('present', 'outside'), ('present', 'inconclusive'),
                                 ('absent', 'outside'), ('indeterminate', 'outside')]]
    rows.append({'signs': {}, 'actual': {'pallor': 'outside'}})
    result = assessed_metrics(rows, 'pallor', 'actual')
    assert result['recall'] == .5
    assert result['target_absent_n'] == 1 and result['fp_rate'] == 1.
    assert result['unknown_n'] == result['indeterminate_n'] == 1


def test_different_positive_and_negative_sources_cannot_train_a_source_shortcut(tmp_path, monkeypatch):
    doc = cohort(tmp_path)
    doc['role'] = 'development'
    doc['sources']['other'] = dict(doc['sources']['study'])
    original = doc['records'][0]
    doc['records'] = []
    for i, (split, status) in enumerate([('train', 'present'), ('train', 'absent'),
                                       ('valid', 'present'), ('valid', 'absent')]):
        name = f'{i}.png'
        (tmp_path / name).write_bytes(str(i).encode())
        doc['records'].append({**original, 'source': 'study' if status == 'present' else 'other',
            'patient_group': f'p{i}', 'image_path': name, 'development_split': split,
            'signs': {'terrys_nails': {'status': status, 'reviewer': 'r1', 'original_label_reference': str(i)}}})
    monkeypatch.setattr(builder, 'reviewed_crop', lambda _: (np.full((32, 32, 3), 127, np.uint8), None))
    with pytest.raises(ValueError, match='TRAIN and calibration'):
        builder.build(write(tmp_path, doc), 'terrys_nails', tmp_path / 'crops')


def test_published_development_adapter_uses_original_bytes_and_explicit_negatives():
    entries = [{'status': status, 'image_path': '/retained/photo.png', 'image_sha256': 'digest',
                'patient_group': 'study:patient1', 'source': 'study', 'view': 'side', 'split': 'holdout'}
               for status in ('present', 'absent', 'indeterminate', 'unknown')]
    rows = development_records({'evaluation_records': entries}, 'pallor')
    assert len(rows) == 2
    assert rows[0]['labels'] == ['pallor'] and rows[1]['labels'] == ['healthy']
    assert all(r['encoding'] == 'original_bytes' and r['view'] == 'side' for r in rows)


def test_empty_retained_photo_is_a_recorded_crop_failure(tmp_path):
    photo = tmp_path / 'empty.jpg'
    photo.write_bytes(b'')
    assert reviewed_crop(photo) == (None, 'invalid_image')
