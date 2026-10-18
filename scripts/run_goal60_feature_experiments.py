"""TRAIN-selected research challengers; VALID is diagnostic, never confirmation."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
from ml.eval.eval_color_sensitivity import b64, ghana_patient_key
from ml.eval.eval_end_to_end import gather, wilson_interval
from ml.eval.sign_features import extract, forest_score, normalized

CONDITIONS = ('terrys_nails', 'pallor')
EXCLUSIONS = ROOT / 'data/raw/goal60_exclusions_v3.json'
ANCHOR = ROOT / 'ml/eval/goal60_withholding_selected_gpu_valid.json'
SOURCE_HOLDOUT = {'terrys_nails': 'yolov8-nails-segmentation-ckvkd',
                  'pallor': 'fingernails-ghana-anemia'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


def group(path, labels):
    source = path.relative_to(ROOT).parts[2]
    if source == 'fingernails-ghana-anemia':
        key = ghana_patient_key(path.name, next(iter(labels)))
    elif source == 'nail-dataset-arthitaya':
        key = path.parent.name + '-' + path.stem
    elif source == 'nail-disease-classification-nihati':
        key = path.stem.split('_', 1)[0]
    else:
        key = re.sub(r'(_jpg|_png|_jpeg)?\.rf\.[0-9a-f]+$', '', path.stem, flags=re.I)
    return source + ':' + key


def collect_one(task):
    path_text, labels, split = task
    path = Path(path_text)
    cv2.setNumThreads(1)
    encoded = b64(path)
    found, reason = extract(encoded) if encoded else (None, 'unreadable')
    return {'path': path.relative_to(ROOT).as_posix(), 'split': split,
            'labels': sorted(labels), 'source': path.relative_to(ROOT).parts[2],
            'group': group(path, labels), 'sha256': sha(path),
            'features': [v if np.isfinite(v) else None for v in found['features']] if found else None,
            'reason': reason, 'skin_ita': found['skin_ita'] if found else None,
            'names': found['names'] if found else None}


def collect(out):
    if (out / 'features.json').exists():
        raise ValueError('Existing feature cache is preserved; use a new experiment directory')
    exclusions = json.loads(EXCLUSIONS.read_text())
    rows = []
    names = None
    tasks = []
    for split in ('train', 'valid'):
        items = gather(split, exclusions, include_authorized=True, include_shapes=True)
        tasks.extend((str(path), sorted(labels), split) for path, labels in sorted(items.items())
                     if split == 'valid' or labels == {'healthy'} or set(CONDITIONS) & labels)
    print(f'Collecting {len(tasks)} full-image records with four workers', flush=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(collect_one, tasks, chunksize=8):
            schema = row.pop('names')
            if schema is not None:
                if names is not None and names != schema:
                    raise ValueError('Feature schema changed')
                names = schema
            rows.append(row)
            if len(rows) % 200 == 0:
                print(f'features {len(rows)}/{len(tasks)}', flush=True)
    fingerprint_paths = [Path(__file__), ROOT / 'ml/eval/sign_features.py', EXCLUSIONS,
                         ROOT / 'ml/eval/eval_color_sensitivity.py', ROOT / 'ml/eval/eval_end_to_end.py',
                         ROOT / 'docs/goal60-existing-label-protocol.md', ROOT / 'data/source_authorizations.json']
    fingerprint_paths += sorted((ROOT / 'ml/infer').glob('*.py'))
    payload = {'names': names, 'rows': rows,
               'fingerprint': {p.relative_to(ROOT).as_posix(): sha(p) for p in fingerprint_paths}}
    dump(out / 'features.json', payload)
    print(json.dumps({'rows': len(rows), 'failures': dict(Counter(r['reason'] for r in rows if r['reason']))}), flush=True)


def fold_rows(rows):
    # Union exact-file and known source/patient-family groups before assigning folds.
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    owners = {}
    for i, r in enumerate(rows):
        for key in ('group:' + r['group'], 'sha:' + r['sha256']):
            if key in owners:
                parent[root(i)] = root(owners[key])
            else:
                owners[key] = i
    clusters = defaultdict(list)
    for i, r in enumerate(rows):
        clusters[root(i)].append(r)
    train, calibration, quarantined = [], [], []
    for members in clusters.values():
        candidates = [r for r in members if r['split'] == 'train']
        if any(r['split'] == 'valid' for r in members):
            quarantined.extend(candidates)
            continue
        canonical = min(r['group'] for r in members)
        bucket = int(hashlib.sha256(('feature-fold-42:' + canonical).encode()).hexdigest(), 16) % 5
        (calibration if bucket == 0 else train).extend(candidates)
    return train, calibration, quarantined


def metric(rows, predictions, condition):
    positive = [r for r in rows if condition in r['labels']]
    healthy = [r for r in rows if r['labels'] == ['healthy']]
    tp = sum(predictions[r['path']] == 'outside' for r in positive)
    fp = sum(predictions[r['path']] == 'outside' for r in healthy)
    incp = sum(predictions[r['path']] == 'inconclusive' for r in positive)
    inch = sum(predictions[r['path']] == 'inconclusive' for r in healthy)
    return {'positives': len(positive), 'tp': tp, 'recall': tp / len(positive) if positive else None,
            'recall_interval': wilson_interval(tp, len(positive)),
            'healthy': len(healthy), 'fp': fp, 'fp_rate': fp / len(healthy) if healthy else None,
            'positive_inconclusive': incp, 'healthy_inconclusive': inch,
            'healthy_correct': len(healthy) - fp - inch}


def fit(out):
    if (out / 'models.lock.json').exists() or (out / 'results.json').exists():
        raise ValueError('Frozen model choices cannot be overwritten')
    cache = json.loads((out / 'features.json').read_text())
    for name, digest in cache['fingerprint'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Stale feature cache: ' + name)
    fit_rows, cal_rows, quarantine = fold_rows(cache['rows'])
    selected = {}
    diagnostics = {}
    holdouts = {}
    for condition in CONDITIONS:
        usable = lambda r: r['features'] is not None and (condition in r['labels'] or r['labels'] == ['healthy'])
        training = [r for r in fit_rows if usable(r)]
        calibration = [r for r in cal_rows if usable(r)]
        y = np.array([int(condition in r['labels']) for r in training], np.int32)
        if set(y) != {0, 1} or not any(r['labels'] == ['healthy'] for r in calibration):
            raise ValueError('Insufficient TRAIN fit/calibration classes')
        x, medians, scales = normalized([r['features'] for r in training])
        cx, _, _ = normalized([r['features'] for r in calibration], medians, scales)
        options = []
        for depth in (4, 8):
            cv2.setRNGSeed(42)
            model = cv2.ml.RTrees_create()
            model.setMaxDepth(depth)
            model.setMinSampleCount(12)
            model.setActiveVarCount(0)
            model.setPriors(np.array([len(y) / (2 * np.sum(y == k)) for k in (0, 1)], np.float32))
            model.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER, 256, 0))
            if not model.train(x, cv2.ml.ROW_SAMPLE, y):
                raise ValueError('Forest training failed')
            scores = forest_score(model, cx)
            healthy_scores = [s for s, r in zip(scores, calibration) if r['labels'] == ['healthy']]
            # Zero new healthy flags on TRAIN calibration; this does not guarantee VALID safety.
            threshold = float(np.nextafter(max(healthy_scores), np.inf))
            pred = {r['path']: 'inconclusive' if r['features'] is None else 'within' for r in cal_rows}
            pred.update({r['path']: 'outside' if s >= threshold else 'within' for r, s in zip(calibration, scores)})
            score = metric(cal_rows, pred, condition)
            model_path = out / f'{condition}_depth{depth}.xml'
            model.save(str(model_path))
            options.append({'depth': depth, 'model': model_path.name, 'model_sha256': sha(model_path),
                            'threshold': threshold, 'calibration': score,
                            'medians': medians.tolist(), 'scales': scales.tolist()})
        chosen = max(options, key=lambda o: (o['calibration']['recall'] or 0, -o['depth']))
        selected[condition] = chosen
        diagnostics[condition] = {'fit_images': len(training), 'fit_positives': int(y.sum()),
                                  'options': options, 'label_basis': 'anemia proxy' if condition == 'pallor' else 'inherited source sign label'}
        # Separate robustness model never sees the named source in fit/calibration.
        hold_source = SOURCE_HOLDOUT[condition]
        hf, hcal, hq = fold_rows([{**r, 'split': 'valid' if r['source'] == hold_source else r['split']}
                                for r in cache['rows']])
        ht = [r for r in hf if usable(r)]
        hc = [r for r in hcal if usable(r)]
        hy = np.array([int(condition in r['labels']) for r in ht], np.int32)
        if set(hy) != {0, 1} or not any(r['labels'] == ['healthy'] for r in hc):
            holdouts[condition] = {'status': 'insufficient fit/calibration classes', 'source': hold_source}
            continue
        hx, hm, hs = normalized([r['features'] for r in ht])
        hcx, _, _ = normalized([r['features'] for r in hc], hm, hs)
        cv2.setRNGSeed(42)
        hmodel = cv2.ml.RTrees_create()
        hmodel.setMaxDepth(4)
        hmodel.setMinSampleCount(12)
        hmodel.setActiveVarCount(0)
        hmodel.setPriors(np.array([len(hy) / (2 * np.sum(hy == k)) for k in (0, 1)], np.float32))
        hmodel.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER, 256, 0))
        if not hmodel.train(hx, cv2.ml.ROW_SAMPLE, hy):
            raise ValueError('Source-holdout training failed')
        scores = forest_score(hmodel, hcx)
        threshold = float(np.nextafter(max(s for s, r in zip(scores, hc) if r['labels'] == ['healthy']), np.inf))
        target = out / f'{condition}_source_holdout.xml'
        hmodel.save(str(target))
        holdouts[condition] = {'status': 'frozen', 'source': hold_source, 'model': target.name,
            'model_sha256': sha(target), 'threshold': threshold, 'medians': hm.tolist(), 'scales': hs.tolist(),
            'fit_images': len(ht), 'fit_positives': int(hy.sum()),
            'quarantined_train_images': len(hq),
            'assessment_scope': 'Named source omitted from this model, not newly acquired evidence'}
    lock = {'experimental': True, 'deployment_approved': False, 'historical_test_used': False,
            'threshold_and_model_selection': 'TRAIN internal grouped calibration only, before VALID scoring',
            'features_sha256': sha(out / 'features.json'), 'selected': selected, 'diagnostics': diagnostics,
            'source_holdout_models': holdouts,
            'cross_split_train_quarantine': [r['path'] for r in quarantine],
            'fit_paths': [r['path'] for r in fit_rows], 'calibration_paths': [r['path'] for r in cal_rows]}
    dump(out / 'models.lock.json', lock)
    print(json.dumps({c: {'depth': o['depth'], 'calibration': o['calibration']} for c, o in selected.items()}), flush=True)


def score_one(row, models):
    pred = {}
    for condition, (model, spec) in models.items():
        if row['features'] is None:
            pred[condition] = 'inconclusive'
        else:
            x, _, _ = normalized([row['features']], np.array(spec['medians']), np.array(spec['scales']))
            pred[condition] = 'outside' if forest_score(model, x)[0] >= spec['threshold'] else 'within'
    return pred


def evaluate(out):
    if (out / 'results.json').exists():
        raise ValueError('Preserve the scored experiment; use a new protocol/directory for another run')
    lock = json.loads((out / 'models.lock.json').read_text())
    if lock['features_sha256'] != sha(out / 'features.json'):
        raise ValueError('Feature membership changed after freeze')
    cache = json.loads((out / 'features.json').read_text())
    for name, digest in cache['fingerprint'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Stale feature cache: ' + name)
    models = {}
    for c, spec in lock['selected'].items():
        if sha(out / spec['model']) != spec['model_sha256']:
            raise ValueError('Model changed after freeze')
        models[c] = (cv2.ml.RTrees_load(str(out / spec['model'])), spec)
    rows = [r for r in json.loads((out / 'features.json').read_text())['rows'] if r['split'] == 'valid']
    anchor = json.loads(ANCHOR.read_text())
    anchor = [{**r, 'path': r['path'].replace('\\', '/')} for r in anchor]
    membership = lambda records: {r['path']: r['labels'] for r in records}
    if (len(membership(rows)) != len(rows) or len(membership(anchor)) != len(anchor)
            or membership(rows) != membership(anchor)):
        raise ValueError('VALID membership differs from frozen anchor')
    predictions = {c: {} for c in CONDITIONS}
    for r in rows:
        for c, verdict in score_one(r, models).items():
            predictions[c][r['path']] = verdict
    result = {'scope': 'Automatic full-image localization development experiment; not endpoint integration or clinical confirmation',
              'historical_test_used': False, 'anchor_sha256': sha(ANCHOR),
              'models_lock_sha256': sha(out / 'models.lock.json'), 'conditions': {}}
    for c in CONDITIONS:
        base = {r['path']: r['findings'][c]['verdict'] for r in anchor}
        # A rescue never overturns an existing decision; it only adds positive calls.
        merged = {p: 'outside' if predictions[c][p] == 'outside' else v for p, v in base.items()}
        new_flags = [r['path'] for r in rows if r['labels'] == ['healthy'] and merged[r['path']] == 'outside' and base[r['path']] != 'outside']
        standalone, rescue = metric(rows, predictions[c], c), metric(rows, merged, c)
        accepted = (not new_flags and rescue['tp'] > metric(rows, base, c)['tp'])
        result['conditions'][c] = {'baseline': metric(rows, base, c), 'standalone': standalone,
            'rescue_diagnostic': rescue, 'new_healthy_flags': new_flags,
            'development_nonregression': accepted, 'clinical_release_eligible': False,
            'source_breakdown': {s: metric([r for r in rows if r['source'] == s], predictions[c], c)
                                 for s in sorted({r['source'] for r in rows})}}
    result['predictions'] = predictions
    result['source_holdout_diagnostics'] = {}
    for c, spec in lock['source_holdout_models'].items():
        if spec['status'] != 'frozen':
            result['source_holdout_diagnostics'][c] = spec
            continue
        target = out / spec['model']
        if sha(target) != spec['model_sha256']:
            raise ValueError('Source-holdout model changed after freeze')
        hmodel = cv2.ml.RTrees_load(str(target))
        held = [r for r in cache['rows'] if r['source'] == spec['source']]
        hp = {r['path']: score_one(r, {c: (hmodel, spec)})[c] for r in held}
        result['source_holdout_diagnostics'][c] = {'source': spec['source'],
            'train': metric([r for r in held if r['split'] == 'train'], hp, c),
            'valid': metric([r for r in held if r['split'] == 'valid'], hp, c)}
    dump(out / 'results.json', result)
    print(json.dumps({c: {k: v for k, v in r.items() if k in ('baseline', 'standalone', 'rescue_diagnostic', 'development_nonregression')}
                     for c, r in result['conditions'].items()}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('collect', 'fit', 'evaluate'))
    parser.add_argument('--out', type=Path, default=ROOT / 'data/raw/goal60_feature_round4')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(2)
    {'collect': collect, 'fit': fit, 'evaluate': evaluate}[args.action](args.out)


if __name__ == '__main__':
    main()
