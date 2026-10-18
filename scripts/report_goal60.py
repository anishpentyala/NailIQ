"""Produce an all-14 scorecard without excluding abstentions or unsupported signs."""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_end_to_end import metrics, wilson_interval
from ml.infer.pipeline import _COLOR_CONDITIONS

CONDITIONS = ['clubbing', 'koilonychia'] + [module.__name__.rsplit('.', 1)[-1] for module in _COLOR_CONDITIONS]


def score(records, shown=False):
    complete = [{**record, 'findings': {**{condition: {} for condition in CONDITIONS}, **record['findings']}}
                for record in records]
    verdict = (lambda row, c: row['findings'][c].get('shown', row['findings'][c].get('verdict'))
               if shown else row['findings'][c].get('verdict'))
    return metrics(complete, verdict)


def healthy_summary(records, shown=False):
    healthy = [r for r in records if r['labels'] == ['healthy']]
    values = [[r['findings'].get(c, {}).get('shown', r['findings'].get(c, {}).get('verdict', 'inconclusive'))
               if shown else r['findings'].get(c, {}).get('verdict', 'inconclusive') for c in CONDITIONS] for r in healthy]
    n = len(values)
    outside = sum('outside' in row for row in values)
    within = sum(all(v == 'within' for v in row) for row in values)
    abstain = sum(any(v not in {'within', 'outside'} for v in row) for row in values)
    return {'n': n, 'any_outside': outside, 'all_within': within, 'any_inconclusive': abstain,
            'any_outside_rate': outside / n if n else None,
            'all_within_rate': within / n if n else None,
            'any_outside_ci95': wilson_interval(outside, n)}


def report(cache):
    records = json.loads(cache.read_text())
    metadata_path = cache.with_suffix('.meta.json')
    metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() else {}
    before, shown = score(records), score(records, True)
    rows = {}
    for condition in CONDITIONS:
        row = shown[condition]
        passing = (row['recall'] is not None and row['recall'] >= 0.6
                   and row['fp_rate'] is not None and row['fp_rate'] <= 0.05)
        measured = any(condition in record['findings'] for record in records)
        status = ('not_evaluated' if not measured else 'no_positive_evidence' if not row['pos']['n']
                  else 'meets_observed_target' if passing else 'below_target')
        rows[condition] = {**row, 'pre_policy': before[condition], 'status': status,
                          'positive_sample_warning': row['pos']['n'] < 30}
    return {'cache': str(cache), 'metadata': metadata, 'conditions': rows,
        'healthy_scan_summary': {'pre_policy': healthy_summary(records), 'shown': healthy_summary(records, True)},
        'observed_target_met_for_all_14': all(row['status'] == 'meets_observed_target' for row in rows.values()),
        'adequate_sample_claim': False,
        'limitations': ['Dataset/community labels, not clinical diagnoses',
                       'Low positive counts are provisional; intervals accompany point estimates',
                       'Geometry measurements and real phone performance are not validated by this scorecard',
                       'Annotation-box runs are oracle diagnostics, never automatic or user-crop accuracy']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = report(args.cache)
    args.out.write_text(json.dumps(result, indent=2))
    for condition, row in result['conditions'].items():
        print(f"{condition:23} {row['status']:25} {row['pos']['outside']}/{row['pos']['n']} positive; "
              f"{row['healthy']['outside']}/{row['healthy']['n']} healthy FP", flush=True)


if __name__ == '__main__':
    main()
