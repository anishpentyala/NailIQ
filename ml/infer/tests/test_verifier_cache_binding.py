import json
from pathlib import Path

import pytest
from scripts import evaluate_goal60_image_verifiers as evaluator


@pytest.mark.parametrize('changed', ['calibrated/models.lock.json', 'train-evidence.json'])
def test_scores_cannot_be_reused_after_model_or_evidence_changes(tmp_path, changed):
    (tmp_path / 'calibrated').mkdir()
    (tmp_path / 'calibrated/models.lock.json').write_text('{}')
    (tmp_path / 'train-evidence.json').write_text('{}')
    meta = {
        'models_lock_sha256': evaluator.file_hash(evaluator.model_lock(tmp_path)),
        'evidence_sha256': evaluator.file_hash(tmp_path / 'train-evidence.json'),
        'verifier_code_sha256': evaluator.file_hash(evaluator.ROOT / 'ml/eval/image_verifier.py'),
        'collector_code_sha256': evaluator.file_hash(Path(evaluator.__file__).resolve()),
    }
    (tmp_path / 'train-evidence.meta.json').write_text(json.dumps(meta))
    evaluator.validate_retained_scores(tmp_path)
    (tmp_path / changed).write_text('{"changed": true}')
    with pytest.raises(ValueError, match='changed models or code'):
        evaluator.validate_retained_scores(tmp_path)


@pytest.mark.parametrize('changed', ['evidence', 'reference', 'split'])
def test_first_stage_reuse_requires_same_signed_reference_and_inputs(tmp_path, monkeypatch, changed):
    previous, current = tmp_path / 'previous', tmp_path / 'current'
    previous.mkdir()
    current.mkdir()
    anchor = tmp_path / 'anchor.json'
    anchor.write_text('[]')
    monkeypatch.setattr(evaluator, 'ANCHOR', anchor)
    for condition in evaluator.STAGES:
        for directory in (previous, current):
            (directory / condition).mkdir()
            (directory / condition / 'manifest.json').write_text('{}')
    evidence = previous / 'train-evidence.json'
    evidence.write_text(json.dumps({c: [{'path': 'photo'}] for c in evaluator.STAGES}))
    fingerprint = {'unchanged_reference': 'hash'}
    lock = {'reference_fingerprint': fingerprint, 'stage1': evaluator.STAGES,
        'reference_cache_sha256': evaluator.file_hash(anchor),
        'calibration_evidence_sha256': evaluator.file_hash(evidence),
        'code': {name: evaluator.file_hash(evaluator.ROOT / name) for name in
                 ('ml/eval/image_verifier.py', 'scripts/prepare_goal60_image_verifiers.py')}}
    (previous / 'thresholds.lock.json').write_text(json.dumps(lock))
    assert evaluator.checked_stage_cache(previous, current, fingerprint)
    path = {'evidence': evidence, 'reference': anchor,
            'split': current / 'pallor/manifest.json'}[changed]
    path.write_text('{"changed": true}')
    with pytest.raises(ValueError, match='changed'):
        evaluator.checked_stage_cache(previous, current, fingerprint)
