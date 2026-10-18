"""Replay complete branches through the same routing decisions as the endpoint."""
from ml.infer.routing import choose, merge_shape


def replay(record, condition, model_metadata, config):
    if record.get('cache_version') != 2 or not isinstance(record.get('branches'), dict):
        raise ValueError('Mixed routing requires version-two branch evidence')
    model_id = config['model']
    if model_id not in model_metadata:
        raise ValueError('Missing model metadata')
    required = ('assisted',) if 'assisted' in record['branches'] else (
        ('legacy',) if config['route'] == 'legacy' else ('detector', 'legacy') if config['route'] == 'detector_fallback' else ('detector',))
    if any(key not in record['branches'] for key in required):
        raise ValueError('Missing required branch evidence')
    branches = {}
    for key in required:
        raw = record['branches'][key]
        if condition not in raw.get('heuristics', {}):
            raise ValueError('Missing measurement evidence')
        model = raw.get('models', {}).get(model_id, {})
        if not raw.get('failure') and model_id not in raw.get('models', {}):
            raise ValueError('Missing probability or model-failure evidence')
        branches[key] = {**raw, 'probs': model.get('probs'), 'model_failure': model.get('failure')}
    finding, key = choose(condition, branches, model_metadata[model_id], config['route'], config.get('rules'))
    if condition in ('clubbing', 'koilonychia'):
        original = record.get('geometry_evidence', {}).get(condition)
        if original is not None:
            finding = merge_shape(original, finding)
            if finding is original:
                key = original.get('route_id')
        elif not record.get('appearance_eligible', {}).get(condition):
            finding = {**finding, 'verdict': record['findings'].get(condition, {}).get('verdict', 'inconclusive')}
            key = record['findings'].get(condition, {}).get('route_id')
    return finding['verdict'], key


def coverage_ok(candidate, baseline, slack=0.02):
    if candidate['healthy']['n'] != baseline['healthy']['n'] or not candidate['healthy']['n']:
        return False
    n = baseline['healthy']['n']
    extra = (candidate['healthy']['inconclusive'] - baseline['healthy']['inconclusive']) / n
    saved = (baseline['healthy']['outside'] - candidate['healthy']['outside']) / n
    return extra <= saved + slack + 1e-12
