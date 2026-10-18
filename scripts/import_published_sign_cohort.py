"""Prepare/audit existing expert labels without requiring new reviewer recruitment."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.published_sign_cohort import load_published_cohort, template

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit('Preserve existing evidence; choose a new output')
    report = load_published_cohort(args.cohort) if args.cohort else template()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'records': len(report.get('rows', [])), 'clinical_release_eligible': False,
                      'out': str(args.out)}))
