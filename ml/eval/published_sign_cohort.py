"""Import partial, already-published expert sign assessments for research only."""
from pathlib import Path
import json

from ml.infer.validation_evidence import file_hash, identity
from scripts.report_goal60 import CONDITIONS


def load_published_cohort(path):
    path = Path(path).resolve()
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('version') != 1 or doc.get('basis') != 'existing_published_expert_assessments':
        raise ValueError('Existing published sign assessments required; no inferred labels')
    if doc.get('patient_grouping_confirmed') is not True or not doc.get('records'):
        raise ValueError('Actual records and documented patient grouping required')
    sources = doc.get('sources', {})
    for source in sources.values():
        if not all(source.get(k) for k in ('publication', 'rights_reference', 'assessment_protocol', 'reviewers')):
            raise ValueError('Document source, reuse rights, assessment method and original reviewers')
        if any(not all(reviewer.get(k) for k in ('qualification', 'evidence_reference'))
               for reviewer in source['reviewers'].values()):
            raise ValueError('Original assessor qualifications need source references')
    seen, hashes, rows = set(), {}, []
    for record in doc['records']:
        source = sources.get(record.get('source'))
        patient = record.get('patient_group')
        if source is None or not isinstance(patient, str) or not patient.strip() or patient in seen:
            raise ValueError('One primary record per documented patient; known source required')
        seen.add(patient)
        photo = (path.parent / record.get('image_path', '')).resolve()
        if not photo.is_file() or record.get('view') not in ('top', 'side', 'unknown'):
            raise ValueError('Retained image and truthful view required')
        digest = file_hash(photo)
        if digest in hashes:
            raise ValueError('Repeated photo across patients; resolve grouping first')
        hashes[digest] = patient
        signs = record.get('signs', {})
        if not signs or set(signs) - set(CONDITIONS):
            raise ValueError('Explicit NailIQ sign assessments required')
        for sign in signs.values():
            if sign.get('status') not in ('present', 'absent', 'indeterminate') or sign.get('reviewer') not in source['reviewers']:
                raise ValueError('Use original present/absent/indeterminate assessment and reviewer')
            if not sign.get('original_label_reference'):
                raise ValueError('Trace each sign to its original assessment; no Hb/disease conversion')
            assessments = sign.get('original_assessments')
            if assessments is not None:
                if not isinstance(assessments, list) or not assessments:
                    raise ValueError('Retain a nonempty list of original assessments')
                for assessment in assessments:
                    if (assessment.get('reviewer') not in source['reviewers'] or
                            assessment.get('status') not in ('present', 'absent', 'indeterminate') or
                            not assessment.get('original_label_reference')):
                        raise ValueError('Each original assessment needs reviewer, status and reference')
                statuses = {a['status'] for a in assessments}
                if len(statuses) > 1 and sign['status'] != 'indeterminate':
                    raise ValueError('Conflicting original assessments must remain indeterminate')
                if len(statuses) == 1 and sign['status'] not in statuses:
                    raise ValueError('Imported status must match unanimous original assessments')
        if 'pallor' in signs and signs['pallor'].get('assessment_target') != 'visible_nail_sign':
            raise ValueError('Pallor requires an explicit visible_nail_sign assessment, never an Hb proxy')
        split = record.get('development_split')
        if split is not None and split not in ('train', 'valid', 'holdout'):
            raise ValueError('Published research split must be train, valid or holdout')
        rows.append({**record, 'image_path': str(photo), 'image_sha256': digest,
            'unknown_signs': sorted(set(CONDITIONS) - set(signs)),
            'verified_all_signs_absent': set(signs) == set(CONDITIONS) and all(s['status'] == 'absent' for s in signs.values()),
            'side_view_available': record['view'] == 'side',
            'geometry_measurement_supported': False,
            'clinical_release_eligible': False})
    return {'scope': 'Partial published sign labels for offline research; not phone/endpoint approval',
            'sha256': identity({'document': doc, 'images': hashes}), 'rows': rows,
            'document': doc, 'clinical_release_eligible': False,
            'limitations': 'Importer enforces documentation/traceability, not independent verification of source claims. '
                           'Partial absence does not mean healthy for all14; top photos do not validate angle/depth.'}


def template():
    return {'version': 1, 'basis': 'existing_published_expert_assessments',
            'patient_grouping_confirmed': False, 'sources': {}, 'records': [],
            'instructions': {'source': ['publication', 'rights_reference', 'assessment_protocol',
                'reviewers: original ID -> qualification and evidence_reference'],
                'record': ['source', 'patient_group', 'image_path', 'view: top|side|unknown',
                    'signs: assessed sign only -> status, reviewer, original_label_reference'],
                'missing_sign': 'Keep unknown; never infer absent from an omitted differential or disease/Hb label',
                'research_split': 'role=development; preassign development_split=train|valid|holdout by patient; holdout is never used for training/calibration',
                'pallor': 'assessment_target=visible_nail_sign is mandatory; laboratory anemia is not pallor',
                'multiple_reviewers': 'Retain original_assessments; conflicting statuses stay indeterminate, no invented consensus',
                'eligibility': 'Research only. Does not write clinical grants or replace fresh phone validation.'}}
