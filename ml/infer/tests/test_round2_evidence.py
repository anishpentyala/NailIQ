import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ml.infer import routing
from scripts import run_goal60_round2 as runner


def test_detector_without_proposal_is_inconclusive_before_fallback(monkeypatch):
    runtime = object.__new__(routing.RoutingRuntime)
    runtime.locator = SimpleNamespace(detect=lambda _: None)
    runtime.branch = lambda image, contour, reason, box, mode, failure=None: {
        'mode': mode, 'failure': failure, 'probs': {'healthy': .1, 'terrys_nails': .9},
        'heuristics': {'terrys_nails': {'label': 'terrys_nails', 'display_name': 'Terry',
                       'verdict': 'outside', 'confidence': .8, 'value': 1, 'unit': '%'}}}
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    monkeypatch.setattr(routing, 'decode_base64_image', lambda _: image)
    monkeypatch.setattr(routing, 'is_flat_frame', lambda _: False)
    monkeypatch.setattr(routing, 'focus_score', lambda _: 1000)
    monkeypatch.setattr(routing, 'extract_best_contour', lambda _: (None, {'is_valid': True}))
    branches, _ = runtime.evidence('image')
    metadata = {'app_conditions': ['terrys_nails']}
    assert routing.choose('terrys_nails', branches, metadata, 'detector')[0]['verdict'] == 'inconclusive'
    verdict, key = routing.choose('terrys_nails', branches, metadata, 'detector_fallback')
    assert (verdict['verdict'], key) == ('outside', 'legacy')


@pytest.mark.parametrize('mutation', ['inputs', 'exclusions', 'rules', 'fingerprint', 'labels', 'membership'])
def test_selection_rejects_changed_evidence(tmp_path, monkeypatch, mutation):
    raw = tmp_path / 'data' / 'raw'
    raw.mkdir(parents=True)
    exclusions = raw / 'goal60_exclusions_v3.json'
    exclusions.write_text('{}')
    photo = tmp_path / 'photo.jpg'
    photo.write_bytes(b'original-photo')
    manifest = tmp_path / 'routing.json'
    manifest.write_text('{}')
    cache = tmp_path / 'cache.json'
    records = [{'path': 'photo.jpg', 'labels': ['healthy']}]
    cache.write_text(json.dumps(records))
    identity = [('photo.jpg', ['healthy'], routing.digest(photo))]
    meta = {'split': 'valid', 'cache_version': 2, 'roi_mode': 'auto',
            'routing_sha256': routing.digest(manifest), 'fingerprint': {'code.py': 'original'},
            'exclusions_sha256': routing.digest(exclusions),
            'input_label_manifest_sha256': hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()}
    cache.with_suffix('.meta.json').write_text(json.dumps(meta))
    monkeypatch.setattr(runner, 'REPO', tmp_path)
    monkeypatch.setattr(runner, 'RAW', raw)
    monkeypatch.setattr(runner, 'evaluation_fingerprint', lambda **_: {'code.py': 'original'})
    current = {photo: {'healthy'}}
    monkeypatch.setattr(runner, 'gather', lambda *args: current)
    assert runner.checked(cache, manifest) == records
    if mutation == 'inputs':
        photo.write_bytes(b'changed-photo')
    elif mutation == 'exclusions':
        exclusions.write_text('{"changed":true}')
    elif mutation == 'rules':
        manifest.write_text('{"changed":true}')
    elif mutation == 'fingerprint':
        monkeypatch.setattr(runner, 'evaluation_fingerprint', lambda **_: {'code.py': 'changed'})
    elif mutation == 'labels':
        current[photo] = {'pallor'}
    else:
        current.clear()
    with pytest.raises(ValueError):
        runner.checked(cache, manifest)


def test_model_runtime_refuses_missing_weight(tmp_path):
    (tmp_path / 'nail_color_classifier_labels.json').write_text(json.dumps({
        'classes': ['healthy', 'pallor'], 'img_size': 224, 'mean': [0, 0, 0], 'std': [1, 1, 1],
        'ensemble': [{'backbone': 'efficientnet_b0', 'weights_file': 'absent.pt', 'temperature': 1}]}))
    with pytest.raises(FileNotFoundError):
        routing.ModelRuntime(tmp_path)
