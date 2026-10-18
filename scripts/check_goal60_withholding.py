"""Strict paired check of the displayed all-sign system; never grants validation."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.withholding_checks import acceptance, subgroup_checks
from ml.infer.validation_evidence import file_hash


def check(candidate, reference, output, exact=True):
    records = json.loads(candidate.read_text())
    result = acceptance(records, json.loads(reference.read_text()), exact)
    result.update({'version': 1, 'phase': 'development_regression',
        'candidate_cache_sha256': file_hash(candidate), 'reference_cache_sha256': file_hash(reference),
        'subgroups': subgroup_checks(records), 'validation_grants_issued': 0})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'protected': all(result['protected'].values()),
        'coverage': all(result['coverage'].values()), 'healthy_scans': result['healthy_scans']['any_outside'],
        'target_count': result['target_count'], 'non_regression_passed': result['non_regression_passed']}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    check(args.candidate, args.reference, args.out)
