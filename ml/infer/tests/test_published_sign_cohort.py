import json
import pytest

from ml.eval.published_sign_cohort import load_published_cohort


def cohort(tmp_path):
    (tmp_path / 'nail.png').write_bytes(b'original retained image fixture')
    return {'version': 1, 'basis': 'existing_published_expert_assessments',
        'patient_grouping_confirmed': True,
        'sources': {'study': {'publication': 'doi:study', 'rights_reference': 'permission:research',
            'assessment_protocol': 'blinded original review',
            'reviewers': {'r1': {'qualification': 'physician', 'evidence_reference': 'study:methods'}}}},
        'records': [{'source': 'study', 'patient_group': 'patient1', 'image_path': 'nail.png', 'view': 'top',
            'signs': {'terrys_nails': {'status': 'absent', 'reviewer': 'r1', 'original_label_reference': 'original:row1'}}}]}


def write(tmp_path, doc):
    path = tmp_path / 'cohort.json'
    path.write_text(json.dumps(doc))
    return path


def test_existing_partial_labels_do_not_require_a_new_reviewer_or_create_healthy_labels(tmp_path):
    result = load_published_cohort(write(tmp_path, cohort(tmp_path)))
    assert len(result['rows'][0]['unknown_signs']) == 13
    assert not result['rows'][0]['verified_all_signs_absent']
    assert not result['rows'][0]['geometry_measurement_supported']
    assert not result['clinical_release_eligible']


def test_laboratory_anemia_is_not_a_visible_sign_label(tmp_path):
    doc = cohort(tmp_path)
    doc['records'][0]['signs'] = {'anemia': {'status': 'present', 'reviewer': 'r1', 'original_label_reference': 'Hb:low'}}
    with pytest.raises(ValueError, match='sign assessments'):
        load_published_cohort(write(tmp_path, doc))


def test_duplicate_photo_cannot_become_a_second_independent_patient(tmp_path):
    doc = cohort(tmp_path)
    doc['records'].append({**doc['records'][0], 'patient_group': 'patient2'})
    with pytest.raises(ValueError, match='Repeated photo'):
        load_published_cohort(write(tmp_path, doc))


def test_assessor_qualification_without_source_reference_is_rejected(tmp_path):
    doc = cohort(tmp_path)
    del doc['sources']['study']['reviewers']['r1']['evidence_reference']
    with pytest.raises(ValueError, match='qualifications'):
        load_published_cohort(write(tmp_path, doc))


def test_side_photo_availability_does_not_validate_measurements(tmp_path):
    doc = cohort(tmp_path)
    doc['records'][0]['view'] = 'side'
    row = load_published_cohort(write(tmp_path, doc))['rows'][0]
    assert row['side_view_available']
    assert not row['geometry_measurement_supported']


def test_hb_cannot_be_relabelled_as_visible_pallor(tmp_path):
    doc = cohort(tmp_path)
    doc['records'][0]['signs']['pallor'] = {
        'status': 'present', 'reviewer': 'r1', 'original_label_reference': 'Hb:low'}
    with pytest.raises(ValueError, match='visible_nail_sign'):
        load_published_cohort(write(tmp_path, doc))


def test_same_patient_cannot_cross_research_splits(tmp_path):
    doc = cohort(tmp_path)
    doc['records'].append({**doc['records'][0], 'development_split': 'holdout'})
    with pytest.raises(ValueError, match='One primary record'):
        load_published_cohort(write(tmp_path, doc))


def test_conflicting_published_reviewers_cannot_become_a_definite_label(tmp_path):
    doc = cohort(tmp_path)
    doc['sources']['study']['reviewers']['r2'] = {'qualification': 'physician', 'evidence_reference': 'study:methods'}
    sign = doc['records'][0]['signs']['terrys_nails']
    sign['original_assessments'] = [{'status': status, 'reviewer': reviewer, 'original_label_reference': reviewer + ':row1'}
                                    for status, reviewer in [('present', 'r1'), ('absent', 'r2')]]
    with pytest.raises(ValueError, match='Conflicting'):
        load_published_cohort(write(tmp_path, doc))
    sign['status'] = 'indeterminate'
    result = load_published_cohort(write(tmp_path, doc))
    assert len(result['rows'][0]['signs']['terrys_nails']['original_assessments']) == 2
