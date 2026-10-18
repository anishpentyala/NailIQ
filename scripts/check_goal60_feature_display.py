"""Check proposed feature rescues against actual shown verdicts, not hidden predictions."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_goal60_feature_experiments import CONDITIONS, ANCHOR, metric, sha, dump
from scripts.diagnose_goal60_feature_budgets import predictions, scores


def shown(row, condition):
    finding = row['findings'][condition]
    if 'shown' not in finding:
        raise ValueError('Actual shown verdict required; never substitute a hidden prediction')
    return finding['shown']


def evaluate(out):
    destination = out / 'display-preservation.json'
    if destination.exists():
        raise ValueError('Preserve existing displayed comparison')
    lock = json.loads((out / 'budgets.lock.json').read_text())
    if (sha(out / 'features.json') != lock['features_sha256'] or sha(out / 'models.lock.json') != lock['models_lock_sha256']):
        raise ValueError('Model/input freeze changed')
    cache = json.loads((out / 'features.json').read_text())
    for name, digest in cache['fingerprint'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Stale features')
    rows = [r for r in cache['rows'] if r['split'] == 'valid']
    anchor = [{**r, 'path': r['path'].replace('\\', '/')} for r in json.loads(ANCHOR.read_text())]
    if {r['path']: r['labels'] for r in rows} != {r['path']: r['labels'] for r in anchor}:
        raise ValueError('VALID identities changed')
    healthy = [r for r in anchor if r['labels'] == ['healthy']]
    anchor_flags = {r['path'] for r in healthy if any(f.get('shown') == 'outside' for f in r['findings'].values())}
    result = {'scope': 'Hypothetical shown positive-only rescue; not endpoint implementation or permission',
        'clinical_release_eligible': False, 'models_lock_sha256': sha(out / 'models.lock.json'),
        'budgets_lock_sha256': sha(out / 'budgets.lock.json'), 'harness_sha256': sha(Path(__file__)),
        'anchor_sha256': sha(ANCHOR), 'actual_displayed_passes': 6,
        'anchor_healthy_any_outside': len(anchor_flags), 'healthy_images': len(healthy), 'conditions': {}}
    for c in CONDITIONS:
        result['conditions'][c] = {}
        base = {r['path']: shown(r, c) for r in anchor}
        for key, spec in lock['choices'][c].items():
            p = predictions(rows, scores(rows, spec, out), spec['threshold'])
            rescue = {path: 'outside' if p[path] == 'outside' else v for path, v in base.items()}
            new_sign_flags = {r['path'] for r in healthy if rescue[r['path']] == 'outside' and base[r['path']] != 'outside'}
            merged_flags = anchor_flags | new_sign_flags
            m = metric(rows, rescue, c)
            result['conditions'][c][key] = {'baseline_shown': metric(rows, base, c),
                'proposed_rescue': m, 'new_sign_healthy_flags': len(new_sign_flags),
                'new_scan_healthy_flags': len(merged_flags - anchor_flags),
                'proposed_healthy_scans_any_outside': len(merged_flags),
                'strict_preservation': not new_sign_flags and m['tp'] > metric(rows, base, c)['tp'],
                'actual_deployed': False, 'clinical_release_eligible': False}
    dump(destination, result)
    print(json.dumps({c: {k: {'recall': r['proposed_rescue']['recall'], 'new_sign_flags': r['new_sign_healthy_flags'],
        'new_scan_flags': r['new_scan_healthy_flags']} for k, r in options.items()} for c, options in result['conditions'].items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    evaluate(parser.parse_args().out)
