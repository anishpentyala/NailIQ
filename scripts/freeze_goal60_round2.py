"""Freeze validated development configuration by model ID, avoiding backbone collisions."""
import argparse
import json
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.infer.routing import RoutingRuntime, digest
from scripts.run_goal60_round2 import checked


def freeze(manifest, cache, verification, device_parity, phone_parity, output):
    checked(cache, manifest)
    parity = json.loads(cache.with_suffix('.parity.json').read_text())
    metadata = json.loads(cache.with_suffix('.meta.json').read_text())
    if parity['mismatches'] != 0 or metadata['split'] != 'valid':
        raise ValueError('Zero-mismatch VALID endpoint replay is required')
    if parity['cache_sha256'] != digest(cache) or parity['manifest_sha256'] != digest(manifest) or metadata['routing_sha256'] != digest(manifest):
        raise ValueError('Parity/cache/manifest mismatch')
    if output.exists():
        raise ValueError('Freeze output already exists; preserve prior experiments')
    runtime = RoutingRuntime(manifest)
    if runtime.model_errors:
        raise ValueError('Cannot freeze unavailable or mismatched models')
    spec = json.loads(manifest.read_text())
    verified = json.loads(verification.read_text())
    device = json.loads(device_parity.read_text())
    phone = json.loads(phone_parity.read_text())
    from scripts.run_goal60_round2 import PASSING
    if (verified['cache_sha256'] != digest(cache) or verified['manifest_sha256'] != digest(manifest)
            or verified['mismatches'] != 0
            or verified.get('unverified_geometry', 0) != 0
            or verified['historical_baseline_comparison']['mismatches'] != 0
            or not all(verified['coverage_constraints'].values())
            or any(spec['conditions'][c] != {'model': 'baseline', 'route': 'legacy'} for c in PASSING)):
        raise ValueError('Verified baseline, full replay, coverage and passing-sign preservation required')
    if (device['mismatches'] or device['manifest_sha256'] != digest(manifest)
            or device['gpu_cache_sha256'] != digest(cache)
            or phone['manifest_sha256'] != digest(manifest)
            or phone['mismatches'] or not phone['passes_shown'] or not phone['passes_pre_policy']):
        raise ValueError('Device and healthy-phone checks must pass before freezing')
    if not runtime.locator and any(config['route'] != 'legacy' for config in spec['conditions'].values()):
        raise ValueError('Selected detector routes require available locator')
    if spec.get('validation_evidence') and (runtime.validation.errors
            or verified.get('non_regression_passed') is not True
            or verified.get('bundle_sha256') != runtime.bundle_sha256):
        raise ValueError('Scoped-evidence freezes require strict displayed regression verification')
    output.mkdir(parents=True)
    lineage = {'source_manifest': str(manifest.resolve()), 'source_manifest_sha256': digest(manifest),
               'development_cache_sha256': digest(cache), 'parity': parity,
               'historical_test_used': False, 'deployment_approved': False,
               'verification_sha256': digest(verification), 'files': {}}
    lineage['device_parity_sha256'] = digest(device_parity)
    lineage['phone_parity_sha256'] = digest(phone_parity)
    active = {config['model'] for config in spec['conditions'].values()}
    # Preserve baseline for explicit comparisons even when every route were changed.
    active.add('baseline')
    models = {}
    for model_id in sorted(active):
        model = runtime.models[model_id]
        destination = output / 'models' / model_id
        destination.mkdir(parents=True)
        for original in model.dependencies:
            path = Path(original)
            shutil.copy2(path, destination / path.name)
        provenance = destination / 'lineage'
        provenance.mkdir()
        for path in sorted(model.directory.glob('*.json')):
            if path.name != model.manifest_path.name:
                shutil.copy2(path, provenance / path.name)
        for path in (model.directory / 'lineage').glob('*'):
            if path.is_file():
                shutil.copy2(path, provenance / path.name)
        models[model_id] = f'models/{model_id}'
    if runtime.locator:
        target = output / 'locator'
        target.mkdir()
        for original in runtime.locator.dependencies:
            path = Path(original)
            shutil.copy2(path, target / path.name)
        spec['locator'] = 'locator'
    elif any(config['route'] != 'legacy' for config in spec['conditions'].values()):
        raise ValueError('Selected detector routes require available locator')
    else:
        spec.pop('locator', None)
    if spec.get('validation_evidence'):
        if runtime.validation.errors:
            raise ValueError('Cannot freeze invalid validation evidence')
        evidence_dir = output / 'validation'
        evidence_dir.mkdir()
        registry = json.loads(runtime.validation.path.read_text())
        for record in registry['records']:
            original = (runtime.validation.path.parent / record['report_file']).resolve()
            destination = evidence_dir / (record['report_sha256'] + '.json')
            shutil.copy2(original, destination)
            record['report_file'] = destination.name
        (evidence_dir / 'registry.json').write_text(json.dumps(registry, indent=2))
        spec['validation_evidence'] = 'validation/registry.json'
    spec['models'] = models
    for path in sorted(output.rglob('*')):
        if path.is_file():
            lineage['files'][path.relative_to(output).as_posix()] = digest(path)
    (output / 'lineage.json').write_text(json.dumps(lineage, indent=2))
    (output / 'routing.json').write_text(json.dumps(spec, indent=2))
    if RoutingRuntime(output / 'routing.json').bundle_sha256 != runtime.bundle_sha256:
        raise ValueError('Frozen relocation changed the candidate semantics')
    print(json.dumps({'frozen': str(output), 'models': models, 'deployment_approved': False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--device-parity', type=Path, required=True)
    parser.add_argument('--phone-parity', type=Path, required=True)
    args = parser.parse_args()
    freeze(args.manifest, args.cache, args.verification, args.device_parity, args.phone_parity, args.out)
