"""TRAIN-calibrated false-alarm frontiers; never used as clinical permission."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
from ml.eval.sign_features import normalized, forest_score
from scripts.run_goal60_feature_experiments import CONDITIONS, ANCHOR, fold_rows, metric, sha, dump


def scores(rows, spec, out):
    if sha(out / spec['model']) != spec['model_sha256']:
        raise ValueError('Frozen model changed')
    good = [r for r in rows if r['features'] is not None]
    x, _, _ = normalized([r['features'] for r in good], np.array(spec['medians']), np.array(spec['scales']))
    model = cv2.ml.RTrees_load(str(out / spec['model']))
    return dict(zip((r['path'] for r in good), forest_score(model, x)))


def predictions(rows, score, threshold):
    return {r['path']: ('inconclusive' if r['path'] not in score else
                       'outside' if score[r['path']] >= threshold else 'within') for r in rows}


def freeze(out):
    destination = out / 'budgets.lock.json'
    if destination.exists() or (out / 'budget-results.json').exists() or (out / 'results.json').exists():
        raise ValueError('Budget choices must freeze before VALID scoring and cannot be overwritten')
    cache = json.loads((out / 'features.json').read_text())
    lock = json.loads((out / 'models.lock.json').read_text())
    if sha(out / 'features.json') != lock['features_sha256']:
        raise ValueError('Frozen features changed')
    _, calibration, _ = fold_rows(cache['rows'])
    chosen = {}
    for c in CONDITIONS:
        chosen[c] = {}
        for budget in (0., .01, .03, .05):
            options = []
            for spec in lock['diagnostics'][c]['options']:
                score = scores(calibration, spec, out)
                healthy = sorted((score[r['path']] for r in calibration if r['labels'] == ['healthy'] and r['path'] in score), reverse=True)
                cap = int(budget * sum(r['labels'] == ['healthy'] for r in calibration))
                threshold = float(np.nextafter(healthy[min(cap, len(healthy) - 1)], np.inf))
                m = metric(calibration, predictions(calibration, score, threshold), c)
                options.append({**spec, 'threshold': threshold, 'budget': budget, 'calibration': m})
            chosen[c][str(budget)] = max(options, key=lambda o: (o['calibration']['recall'] or 0, -o['depth']))
    dump(destination, {'scope': 'Diagnostic TRAIN-selected budget frontier; no VALID selection or clinical grants',
        'features_sha256': sha(out / 'features.json'), 'models_lock_sha256': sha(out / 'models.lock.json'),
        'harness_sha256': sha(Path(__file__)), 'choices': chosen})
    print('TRAIN budget choices frozen', flush=True)


def evaluate(out):
    destination = out / 'budget-results.json'
    if destination.exists():
        raise ValueError('Preserve scored budget evidence')
    lock = json.loads((out / 'budgets.lock.json').read_text())
    if (sha(out / 'features.json') != lock['features_sha256'] or sha(out / 'models.lock.json') != lock['models_lock_sha256']
            or sha(Path(__file__)) != lock['harness_sha256']):
        raise ValueError('Budget choices or harness changed after freeze')
    cache = json.loads((out / 'features.json').read_text())
    for name, digest in cache['fingerprint'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Stale feature cache')
    rows = [r for r in cache['rows'] if r['split'] == 'valid']
    anchor = [{**r, 'path': r['path'].replace('\\', '/')} for r in json.loads(ANCHOR.read_text())]
    if {r['path']: r['labels'] for r in rows} != {r['path']: r['labels'] for r in anchor}:
        raise ValueError('VALID identities changed')
    result = {'scope': lock['scope'], 'clinical_release_eligible': False,
              'budgets_lock_sha256': sha(out / 'budgets.lock.json'), 'anchor_sha256': sha(ANCHOR), 'conditions': {}}
    for c in CONDITIONS:
        result['conditions'][c] = {}
        base = {r['path']: r['findings'][c]['verdict'] for r in anchor}
        for key, spec in lock['choices'][c].items():
            p = predictions(rows, scores(rows, spec, out), spec['threshold'])
            rescue = {path: 'outside' if p[path] == 'outside' else v for path, v in base.items()}
            new = [r['path'] for r in rows if r['labels'] == ['healthy'] and rescue[r['path']] == 'outside' and base[r['path']] != 'outside']
            m = metric(rows, rescue, c)
            result['conditions'][c][key] = {'depth': spec['depth'], 'threshold': spec['threshold'],
                'standalone': metric(rows, p, c), 'rescue_diagnostic': m,
                'new_healthy_flags': new, 'strict_rescue_nonregression': not new and m['tp'] > metric(rows, base, c)['tp']}
    dump(destination, result)
    print(json.dumps({c: {k: {'recall': v['rescue_diagnostic']['recall'], 'new_healthy_flags': len(v['new_healthy_flags'])}
          for k, v in options.items()} for c, options in result['conditions'].items()}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'evaluate'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    cv2.setNumThreads(2)
    {'freeze': freeze, 'evaluate': evaluate}[args.action](args.out)
