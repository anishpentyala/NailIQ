"""Freeze TRAIN-calibrated image verification, then report strict development rescues."""
import argparse
import base64
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.image_verifier import StageEvidence, STAGES, raw_stage, shadow, threshold, verifier_score, runtime_reference
from ml.eval.eval_color_sensitivity import b64
from ml.eval.eval_end_to_end import evaluation_fingerprint, gather
from ml.eval.withholding_checks import acceptance, subgroup_checks
from ml.infer.routing import ModelRuntime, RoutingRuntime
from ml.infer.skin_tone import skin_tone_summary
from ml.infer.validation_evidence import file_hash
from scripts.report_goal60 import CONDITIONS, score
from scripts.run_goal60_feature_experiments import metric

REFERENCE = ROOT / 'data/raw/goal60_withholding_round3/selected.json'
ANCHOR = ROOT / 'ml/eval/goal60_withholding_selected_gpu_valid.json'


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def model_lock(out):
    return out / 'calibrated/models.lock.json'


def validate_retained_scores(out):
    meta = json.loads((out / 'train-evidence.meta.json').read_text())
    for path, key in ((model_lock(out), 'models_lock_sha256'),
                      (out / 'train-evidence.json', 'evidence_sha256'),
                      (ROOT / 'ml/eval/image_verifier.py', 'verifier_code_sha256'),
                      (Path(__file__).resolve(), 'collector_code_sha256')):
        if file_hash(path) != meta[key]:
            raise ValueError('Retained calibration scores belong to changed models or code')


def development_records(manifest, condition):
    result = []
    for original in manifest['evaluation_records']:
        if 'image_path' not in original:
            result.append(original)
            continue
        if original['status'] not in ('present', 'absent'):
            continue
        result.append({**original, 'path': original['image_path'],
            'group': original['patient_group'], 'sha256': original['image_sha256'],
            'labels': [condition] if original['status'] == 'present' else ['healthy'],
            'skin_ita': None, 'encoding': 'original_bytes'})
    return result


def load_models(out, device):
    lock = json.loads(model_lock(out).read_text())
    models = {}
    for c, spec in lock['conditions'].items():
        directory = Path(spec['directory'])
        if file_hash(directory / 'nail_color_classifier_labels.json') != spec['manifest_sha256']:
            raise ValueError('Frozen model manifest changed')
        for member in spec['members']:
            if file_hash(directory / member['weights_file']) != member['sha256']:
                raise ValueError('Frozen model weights changed')
        if file_hash(out / c / 'manifest.json') != spec['data_manifest_sha256']:
            raise ValueError('Training inventory changed')
        models[c] = ModelRuntime(directory, device)
    return models


def checked_anchor():
    meta = json.loads(ANCHOR.with_suffix('.meta.json').read_text())
    normalized = lambda values: {str(Path(k).resolve()): v for k, v in values.items()}
    previous = normalized(meta['fingerprint'])
    current = {path: file_hash(path) for path in previous}
    if any(str(path.resolve()) not in previous for path in (ROOT / 'ml/infer').glob('*.py')):
        raise ValueError('New inference code is absent from the reference fingerprint')
    if current != previous:
        differences = [k for k in set(current) | set(previous) if current.get(k) != previous.get(k)]
        raise ValueError('Reference endpoint cache is stale: ' + ','.join(differences))
    records = json.loads(ANCHOR.read_text())
    exclusions = ROOT / 'data/raw/goal60_exclusions_v3.json'
    if file_hash(exclusions) != meta['exclusions_sha256']:
        raise ValueError('Reference exclusions changed')
    items = gather('valid', json.loads(exclusions.read_text()), meta.get('include_authorized', False), meta.get('include_shapes', False))
    inputs = [(str(path.relative_to(ROOT)), sorted(labels), file_hash(path)) for path, labels in sorted(items.items(), key=lambda kv: str(kv[0]))]
    if hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest() != meta['input_label_manifest_sha256']:
        raise ValueError('Reference input labels/images changed')
    for r in records:
        if set(r['findings']) != set(CONDITIONS) or any('shown' not in f for f in r['findings'].values()):
            raise ValueError('Complete actual displayed reference required')
    return records, current


def checked_stage_cache(previous, out, fingerprint):
    lock = json.loads((previous / 'thresholds.lock.json').read_text())
    if (lock['reference_fingerprint'] != fingerprint or lock['stage1'] != STAGES
            or lock['reference_cache_sha256'] != file_hash(ANCHOR)
            or lock['calibration_evidence_sha256'] != file_hash(previous / 'train-evidence.json')):
        raise ValueError('First-stage cache provenance changed')
    for name in ('ml/eval/image_verifier.py', 'scripts/prepare_goal60_image_verifiers.py'):
        recorded = {Path(p).as_posix(): value for p, value in lock['code'].items()}
        if recorded.get(name) != file_hash(ROOT / name):
            raise ValueError('First-stage extraction or split code changed')
    rows = json.loads((previous / 'train-evidence.json').read_text())
    indexed = {}
    for condition in STAGES:
        if file_hash(previous / condition / 'manifest.json') != file_hash(out / condition / 'manifest.json'):
            raise ValueError('First-stage cache data membership changed')
        indexed[condition] = {r['path']: r for r in rows[condition]}
        if len(indexed[condition]) != len(rows[condition]):
            raise ValueError('Duplicate first-stage cache rows')
    return indexed


def collect_development(out, device, stage_cache=None, fingerprint=None):
    models = load_models(out, device)
    runtime = StageEvidence(REFERENCE, device)
    metadata = {k: model.metadata for k, model in runtime.models.items()}
    cached = checked_stage_cache(stage_cache, out, fingerprint) if stage_cache else None
    crop_runtime = None
    if cached is not None:
        crop_runtime = StageEvidence(REFERENCE, device)
        crop_runtime.models = MappingProxyType({})
        crop_runtime.locator = None
    manifests = {c: json.loads((out / c / 'manifest.json').read_text()) for c in models}
    tasks = {}
    for c, manifest in manifests.items():
        for r in development_records(manifest, c):
            if r['split'] in ('valid', 'holdout'):
                tasks.setdefault(r['path'], {})[c] = r
    collected = {c: [] for c in models}
    parity_checks = 0
    for i, (path, entries) in enumerate(sorted(tasks.items())):
        photo = ROOT / path
        if any(file_hash(photo) != r['sha256'] for r in entries.values()):
            raise ValueError('Development original changed')
        originals = [r for r in entries.values() if r.get('encoding') == 'original_bytes']
        if originals and len(originals) != len(entries):
            raise ValueError('Conflicting original-versus-simulated photo provenance')
        encoded = (base64.b64encode(photo.read_bytes()).decode() if originals else b64(photo))
        if originals and any(r['view'] != 'top' for r in originals):
            encoded = ''
        branches, _ = (crop_runtime or runtime).evidence(encoded or '')
        record = {'cache_version': 2, 'branches': branches}
        parity = cached is not None and i % 256 == 0
        if parity:
            full_branches, _ = runtime.evidence(encoded or '')
            for key in ('bbox', 'failure', 'heuristics', 'quality', 'roi_only', 'skin_ita'):
                if branches['legacy'].get(key) != full_branches['legacy'].get(key):
                    raise ValueError('Cached-stage crop extraction differs from the full runtime')
            parity_checks += 1
        for c, entry in entries.items():
            if cached is None:
                stage = raw_stage(record, metadata, c)
            else:
                saved = cached[c][path]
                if any(saved.get(k) != entry.get(k) for k in ('sha256', 'labels', 'group', 'split')):
                    raise ValueError('First-stage cached labels, image or group changed')
                stage = saved['stage1']
                if stage not in ('within', 'outside', 'inconclusive'):
                    raise ValueError('Invalid cached first-stage verdict')
                if parity and stage != raw_stage({'cache_version': 2, 'branches': full_branches}, metadata, c):
                    raise ValueError('Frozen first-stage cache differs from fresh inference')
            probability, reason = verifier_score(encoded or '', branches, models[c], c)
            if originals and entry['view'] != 'top':
                reason = 'top_view_unavailable'
            collected[c].append({**entry, 'stage1': stage, 'probability': probability, 'failure': reason})
        if i % 100 == 0:
            print(f'TRAIN-derived calibration/omitted images {i+1}/{len(tasks)}', flush=True)
    dump(out / 'train-evidence.json', collected)
    dump(out / 'train-evidence.meta.json', {
        'models_lock_sha256': file_hash(model_lock(out)),
        'evidence_sha256': file_hash(out / 'train-evidence.json'),
        'verifier_code_sha256': file_hash(ROOT / 'ml/eval/image_verifier.py'),
        'collector_code_sha256': file_hash(Path(__file__).resolve()),
        'stage_cache': str(stage_cache.resolve()) if stage_cache else None,
        'stage_cache_lock_sha256': file_hash(stage_cache / 'thresholds.lock.json') if stage_cache else None,
        'fresh_stage_parity_images': parity_checks,
    })
    return collected


def calibrate(out, device, stage_cache=None):
    if (out / 'thresholds.lock.json').exists():
        raise ValueError('Frozen cutoffs cannot be overwritten')
    records, fingerprint = checked_anchor()
    evidence_path = out / 'train-evidence.json'
    if evidence_path.exists():
        load_models(out, device)
        validate_retained_scores(out)
        evidence = json.loads(evidence_path.read_text())
        image_hashes = {}
        for c, rows in evidence.items():
            expected = [r for r in development_records(json.loads((out / c / 'manifest.json').read_text()), c)
                        if r['split'] in ('valid', 'holdout')]
            indexed = {(r['path'], r['split']): r for r in rows}
            if len(indexed) != len(rows) or set(indexed) != {(r['path'], r['split']) for r in expected}:
                raise ValueError('Retained calibration membership changed')
            for r in expected:
                saved = indexed[(r['path'], r['split'])]
                if any(saved.get(k) != r.get(k) for k in ('labels', 'group', 'sha256')):
                    raise ValueError('Retained calibration labels/patients changed')
                image_hashes.setdefault(r['path'], r['sha256'])
        for path, digest in image_hashes.items():
            if file_hash(ROOT / path) != digest:
                raise ValueError('Retained calibration original changed')
    else:
        evidence = collect_development(out, device, stage_cache, fingerprint)
    choices = {c: threshold([r for r in rows if r['split'] == 'valid']) for c, rows in evidence.items()}
    lock = {'version': 1, 'thresholds': choices, 'stage1': STAGES,
        'models_lock_sha256': file_hash(model_lock(out)),
        'calibration_evidence_sha256': file_hash(out / 'train-evidence.json'),
        'calibration_meta_sha256': file_hash(out / 'train-evidence.meta.json'),
        'reference_cache_sha256': file_hash(ANCHOR), 'reference_fingerprint': fingerprint,
        'code': {str(p.relative_to(ROOT)): file_hash(p) for p in (
            Path(__file__).resolve(), ROOT / 'ml/eval/image_verifier.py', ROOT / 'scripts/prepare_goal60_image_verifiers.py',
            ROOT / 'scripts/freeze_goal60_image_verifiers.py', ROOT / 'ml/train/train_color_classifier.py',
            ROOT / 'ml/train/model_average.py', ROOT / 'ml/train/train_classifier.py',
            ROOT / 'scripts/train_goal60_image_verifiers.py')},
        'clinical_release_eligible': False, 'confirmation_used': False,
        'selection': 'zero additional TRAIN-calibration target-negative flags; no VALID threshold selection',
        'limitations': ['First-stage candidate ancestry has seen original TRAIN omitted sources/patients',
            'Omitted cohorts are stage-two-only development holdouts, not independent full-pipeline confirmation']}
    dump(out / 'thresholds.lock.json', lock)
    print(json.dumps({'frozen_thresholds': choices}), flush=True)


def check_lock(out):
    lock = json.loads((out / 'thresholds.lock.json').read_text())
    for path, key in ((model_lock(out), 'models_lock_sha256'),
                      (out / 'train-evidence.json', 'calibration_evidence_sha256'),
                      (out / 'train-evidence.meta.json', 'calibration_meta_sha256'),
                      (ANCHOR, 'reference_cache_sha256')):
        if file_hash(path) != lock[key]:
            raise ValueError('Frozen inputs changed')
    for path, digest in lock['code'].items():
        if file_hash(ROOT / path) != digest:
            raise ValueError('Verifier code changed after threshold freeze')
    records, fingerprint = checked_anchor()
    if lock['reference_fingerprint'] != fingerprint or lock['stage1'] != STAGES:
        raise ValueError('First-stage choices changed')
    return lock, records


def evaluate(out, device):
    if (out / 'results.json').exists():
        raise ValueError('Preserve previous evaluation')
    lock, records = check_lock(out)
    models = load_models(out, device)
    runtime = RoutingRuntime(runtime_reference(REFERENCE, device))
    metadata = {k: m.metadata for k, m in runtime.models.items()}
    proposed, predictions = copy.deepcopy(records), {c: [] for c in models}
    for i, (original, candidate) in enumerate(zip(records, proposed)):
        path = original['path'].replace('\\', '/')
        image = ROOT / path
        encoded = b64(image)
        for c, model in models.items():
            stage1 = raw_stage(original, metadata, c)
            probability, reason = verifier_score(encoded or '', original['branches'], model, c)
            verdict = shadow(original['findings'][c]['shown'], stage1, probability, lock['thresholds'][c])
            candidate['findings'][c]['shown'] = verdict['hypothetical_shown']
            predictions[c].append({'path': path, 'stage1': stage1, 'probability': probability,
                'failure': reason, **verdict})
        candidate['source'] = path.split('/')[2]
        ita = original['branches']['legacy'].get('skin_ita')
        candidate['skin_tone_band'] = (skin_tone_summary(ita) or {}).get('band', 'unknown')
        if i % 100 == 0:
            print(f'Reused VALID shadow evaluation {i+1}/{len(records)}', flush=True)
    comparison = acceptance(proposed, records, exact_protected=True)
    all14 = score(proposed, True)
    new_sign_flags = {c: sum(old['labels'] == ['healthy'] and old['findings'][c]['shown'] != 'outside'
                         and new['findings'][c]['shown'] == 'outside' for old, new in zip(records, proposed)) for c in CONDITIONS}
    correct_positives_preserved = all(all14[c]['pos']['outside'] >= comparison['reference'][c]['pos']['outside'] for c in CONDITIONS)
    results = {'scope': 'Frozen positive-only hypothetical additions on reused VALID; actual endpoint unchanged',
        'reference_routing_manifest': str(REFERENCE.resolve()), 'reference_cache': str(ANCHOR.resolve()),
        'actual_displayed_passes': sum(v['recall'] is not None and v['recall'] >= .6 and v['fp_rate'] is not None and v['fp_rate'] <= .05 for v in score(records, True).values()),
        'hypothetical_all14_passes': sum(v['recall'] is not None and v['recall'] >= .6 and v['fp_rate'] is not None and v['fp_rate'] <= .05 for v in all14.values()),
        'comparison': comparison, 'all14': all14, 'subgroups': subgroup_checks(proposed),
        'new_sign_healthy_flags': new_sign_flags, 'all_correct_positives_preserved': correct_positives_preserved,
        'strict_preservation': comparison['non_regression_passed'] and correct_positives_preserved and not any(new_sign_flags.values()),
        'models_lock_sha256': file_hash(model_lock(out)),
        'thresholds_lock_sha256': file_hash(out / 'thresholds.lock.json'),
        'clinical_release_eligible': False, 'deployment_approved': False,
        'omitted_stage_two_cohorts': {}, 'failures': {c: dict(Counter(r['failure'] for r in rows if r['failure'])) for c, rows in predictions.items()}}
    evidence = json.loads((out / 'train-evidence.json').read_text())
    for c, rows in evidence.items():
        subset = [r for r in rows if r['split'] == 'holdout']
        calls = {r['path']: 'outside' if shadow('inconclusive', r['stage1'], r['probability'], lock['thresholds'][c])['added_positive'] else 'inconclusive' for r in subset}
        results['omitted_stage_two_cohorts'][c] = metric(subset, calls, c)
    dump(out / 'predictions.json', predictions)
    dump(out / 'hypothetical.json', proposed)
    dump(out / 'results.json', results)
    print(json.dumps({k: results[k] for k in ('actual_displayed_passes', 'hypothetical_all14_passes', 'clinical_release_eligible')}), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('phase', choices=('calibrate', 'evaluate'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--device', choices=('cpu', 'cuda:0'), default='cuda:0')
    ap.add_argument('--stage-cache', type=Path, help='Reuse only hash-bound unchanged first-stage verdicts')
    args = ap.parse_args()
    import torch
    torch.set_num_threads(2)
    if args.phase == 'calibrate':
        calibrate(args.out, args.device, args.stage_cache)
    else:
        evaluate(args.out, args.device)
