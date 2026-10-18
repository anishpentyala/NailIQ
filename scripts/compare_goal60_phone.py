"""Compare identical healthy-phone captures on CPU and GPU."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.infer.validation_evidence import file_hash


def compare(cpu_path, gpu_path, manifest, output):
    cpu, gpu = [json.loads(p.read_text()) for p in (cpu_path, gpu_path)]
    if not gpu.get('routing_manifest') or (ROOT / gpu['routing_manifest']).resolve() != manifest.resolve():
        raise ValueError('GPU phone result must belong to the requested manifest')
    if (cpu['source_hashes'] != gpu['source_hashes'] or not cpu['source_hashes']
            or cpu.get('bundle_sha256') != gpu.get('bundle_sha256')
            or not gpu.get('bundle_sha256')):
        raise ValueError('Phone sources and semantic bundles must match')
    for report in (cpu, gpu):
        for path, expected in report['fingerprint'].items():
            if file_hash(ROOT / path) != expected:
                raise ValueError('Stale phone dependency evidence')
    left = {r['mode']: r for r in cpu['rows']}
    right = {r['mode']: r for r in gpu['rows']}
    required = {'raw', 'guide', 'raw_assisted', 'guide_assisted'}
    if set(left) != required or set(right) != required:
        raise ValueError('All four capture modes required')
    errors, checked = [], 0
    for mode in sorted(required):
        a = {f['label']: f for f in left[mode]['findings']}
        b = {f['label']: f for f in right[mode]['findings']}
        if set(a) != set(b) or len(a) != 14:
            raise ValueError('Complete fourteen-sign endpoint responses required')
        for condition in a:
            fields = ('verdict', 'route_id', 'agreement', 'evidence_type', 'failure_reason', 'unit')
            values = lambda f: (f.get('unvalidated_verdict', f['verdict']), *(f.get(k) for k in fields))
            checked += 1
            if values(a[condition]) != values(b[condition]):
                errors.append({'mode': mode, 'condition': condition})
    result = {'modes': 4, 'subjects': 1, 'findings_checked': checked,
        'mismatches': len(errors), 'differences': errors,
        'passes_shown': all(r['passes_shown'] for r in (cpu, gpu)),
        'passes_pre_policy': all(r['passes_pre_policy'] for r in (cpu, gpu)),
        'cpu_sha256': file_hash(cpu_path), 'gpu_sha256': file_hash(gpu_path),
        'manifest_sha256': file_hash(manifest), 'bundle_sha256': gpu['bundle_sha256'],
        'scope': 'One retained healthy subject; bounded device regression, not clinical validation'}
    output.write_text(json.dumps(result, indent=2))
    if errors or not result['passes_shown'] or not result['passes_pre_policy']:
        raise ValueError('Healthy-phone device regression failed')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cpu', 'gpu', 'manifest', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    compare(args.cpu, args.gpu, args.manifest, args.out)
