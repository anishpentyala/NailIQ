"""Reviewed paired-photo cohorts; no inferred labels or dropped failed captures."""
import json
from pathlib import Path

from ml.infer.validation_evidence import file_hash, identity
from scripts.report_goal60 import CONDITIONS


def load_cohort(path):
    path = Path(path).resolve()
    document = json.loads(path.read_text(encoding='utf-8'))
    if document.get('version') != 1 or document.get('role') not in ('development', 'confirmation'):
        raise ValueError('Versioned reviewed cohort required')
    if not document.get('patients'):
        raise ValueError('No reviewed patients; the template is not clinical evidence')
    reviewers = document.get('reviewers', {})
    if not reviewers or any(not r.get('qualification') for r in reviewers.values()):
        raise ValueError('Qualified reviewer identifiers and qualifications required')
    if document.get('blinded_review') is not True or document.get('patient_independence_confirmed') is not True:
        raise ValueError('Blinded review and confirmed patient grouping required')
    seen, hashes, rows = set(), {}, []
    for patient in document['patients']:
        group = patient.get('patient_group')
        if not isinstance(group, str) or not group.strip() or group in seen:
            raise ValueError('One primary capture pair per confirmed patient group required')
        seen.add(group)
        if patient.get('primary_capture_index') != 1 or not patient.get('rights_reference'):
            raise ValueError('First prescribed pair and permitted reuse reference required')
        if not patient.get('source') or not patient.get('skin_tone_band'):
            raise ValueError('Source and skin-tone metadata required (use unknown explicitly)')
        if patient.get('photo_adequacy') not in ('adequate', 'inadequate', 'indeterminate'):
            raise ValueError('Assess photo adequacy separately; do not drop inadequate photos')
        signs = patient.get('signs', {})
        if set(signs) != set(CONDITIONS):
            raise ValueError('Review all 14 signs; preserve indeterminate assessments')
        for sign in signs.values():
            if sign.get('status') not in ('present', 'absent', 'indeterminate') or sign.get('reviewer') not in reviewers:
                raise ValueError('Every sign needs a reviewed status and reviewer')
        photos = {}
        for view in ('side', 'top'):
            relative = patient.get(view + '_path')
            photo = (path.parent / relative).resolve() if relative else None
            if photo is None or not photo.is_file():
                raise ValueError('Every patient requires retained side and top capture files')
            sha = file_hash(photo)
            if sha in hashes:
                raise ValueError('Duplicate photo across patients/views; adjudicate grouping first')
            hashes[sha] = group
            photos[view] = {'path': str(photo), 'sha256': sha}
        labels = [c for c in CONDITIONS if signs[c]['status'] == 'present']
        if all(signs[c]['status'] == 'absent' for c in CONDITIONS):
            labels = ['healthy']
        row = {**patient, 'path': group, 'labels': sorted(labels), 'photos': photos}
        rows.append(row)
    return {'document': document, 'rows': rows, 'sha256': identity({'document': document,
            'photos': {r['patient_group']: {v: p['sha256'] for v, p in r['photos'].items()} for r in rows}})}


def separate_cohorts(development, confirmation):
    groups = {r['patient_group'] for r in development['rows']}
    images = {p['sha256'] for r in development['rows'] for p in r['photos'].values()}
    if any(r['patient_group'] in groups or any(p['sha256'] in images for p in r['photos'].values())
           for r in confirmation['rows']):
        raise ValueError('Confirmation patients/photos overlap development')
    if development['document']['role'] != 'development' or confirmation['document']['role'] != 'confirmation':
        raise ValueError('Separate development and confirmation cohorts required')


def template():
    return {'version': 1, 'role': 'confirmation', 'blinded_review': False,
        'patient_independence_confirmed': False, 'reviewers': {}, 'patients': [],
        'instructions': {'minimum_planning_counts': {'positive_patients_per_claimed_sign': 150, 'healthy_patients': 400},
            'reviewer': {'qualification': 'Clinical qualification, recorded by the reviewer'},
            'patient_fields': ['patient_group', 'primary_capture_index=1', 'side_path', 'top_path',
                'source', 'skin_tone_band', 'rights_reference', 'photo_adequacy', 'signs'],
            'signs': {c: {'status': 'present|absent|indeterminate', 'reviewer': 'registered reviewer ID'} for c in CONDITIONS},
            'warnings': ['Do not infer absent signs from a source class label',
                         'Retain poor-quality known-positive captures as misses',
                         'No patient labels have been supplied in this template']}}
