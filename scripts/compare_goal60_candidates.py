"""Rank automatic VALID experiments under the recorded all-14 selection protocol."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval import tune_color_decision as tuner
from ml.eval.eval_end_to_end import evaluation_fingerprint, metrics
from ml.infer import color_classifier, color_fusion
from scripts.report_goal60 import CONDITIONS
from scripts.goal60_evidence import same_fingerprint


def summarize(records):
    complete = [{**r, '_original': r,
                 'findings': {**{c: {} for c in CONDITIONS}, **r['findings']}} for r in records]
    rows = metrics(complete, lambda r, c: tuner.replay(r['_original'], c))
    passing = lambda row: (row['recall'] is not None and row['recall'] >= 0.6
                           and row['fp_rate'] is not None and row['fp_rate'] <= 0.05)
    count = sum(passing(rows[c]) for c in CONDITIONS)
    recall = sum((rows[c]['recall'] or 0) if rows[c]['fp_rate'] is not None
                 and rows[c]['fp_rate'] <= 0.05 else 0 for c in CONDITIONS) / len(CONDITIONS)
    healthy = sum(rows[c]['healthy_correct_rate'] or 0 for c in CONDITIONS) / len(CONDITIONS)
    return rows, [count, recall, healthy]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True, help='JSON list of name, model_dir, locator_dir, cache, rules')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    defaults = (dict(color_classifier.CLASS_CONFIDENCE_THRESHOLD), dict(color_fusion.OVR_THRESHOLD),
                dict(color_fusion.HEURISTIC_MIN_CNN_SUPPORT))
    results = []
    for item in json.loads(args.spec.read_text()):
        model = (REPO / item['model_dir']).resolve()
        locator = (REPO / item['locator_dir']).resolve() if item.get('locator_dir') else None
        cache, rule_path = REPO / item['cache'], REPO / item['rules']
        metadata = json.loads(cache.with_suffix('.meta.json').read_text())
        rules = json.loads(rule_path.read_text())
        if metadata.get('split') != 'valid' or metadata.get('roi_mode') == 'annotation':
            raise SystemExit(f"{item['name']}: only automatic VALID candidates may be ranked")
        manifest_path = model / 'nail_color_classifier_labels.json'
        if not same_fingerprint(metadata['fingerprint'], evaluation_fingerprint(model, locator)):
            raise SystemExit(f"{item['name']}: stale endpoint evidence")
        if (rules.get('valid_cache_sha256') != hashlib.sha256(cache.read_bytes()).hexdigest()
                or rules.get('candidate_manifest_sha256') != hashlib.sha256(manifest_path.read_bytes()).hexdigest()):
            raise SystemExit(f"{item['name']}: rule/evidence mismatch")
        if rules.get('min_recall', 0) < 0.6 or rules.get('max_fp', 1) > 0.05:
            raise SystemExit('Do not weaken the target during selection')
        for table, original in zip((color_classifier.CLASS_CONFIDENCE_THRESHOLD, color_fusion.OVR_THRESHOLD,
                                    color_fusion.HEURISTIC_MIN_CNN_SUPPORT), defaults):
            table.clear()
            table.update(original)
        color_classifier._MODELS, color_classifier._LABELS_PATH = model, manifest_path
        color_classifier.configure_manifest_rules()
        manifest = color_classifier.model_metadata()
        tuner._RUN_COVERAGE = frozenset(manifest.get('app_conditions', []) + manifest.get('appearance_conditions', []))
        tuner._RUN_APPEARANCE_RULES = manifest.get('appearance_rules', {})
        tuner._RUN_SHAPE_ELIGIBLE = (metadata.get('include_shapes') is True
                                    and 'side geometry excluded' in metadata.get('scope', ''))
        records = json.loads(cache.read_text())
        bad, rounding = tuner.parity(records)
        if bad:
            raise SystemExit(f"{item['name']}: replay differs from endpoint")
        for condition, (floor, ovr, support) in rules['rules'].items():
            for table, value in ((color_classifier.CLASS_CONFIDENCE_THRESHOLD, floor),
                                 (color_fusion.OVR_THRESHOLD, ovr), (color_fusion.HEURISTIC_MIN_CNN_SUPPORT, support)):
                if value is None:
                    table.pop(condition, None)
                else:
                    table[condition] = value
        rows, rank = summarize(records)
        source_rows = {source: summarize([r for r in records if Path(r['path']).parts[2] == source])[0]
                       for source in sorted({Path(r['path']).parts[2] for r in records})}
        results.append({**item, 'rank': rank + [-len(manifest['ensemble']), -bool(locator)],
                        'conditions': rows, 'by_source': source_rows, 'rounding_cases': rounding})
    results.sort(key=lambda row: row['rank'], reverse=True)
    args.out.write_text(json.dumps({'scope': 'VALID-selected pre-policy experiments; no deployment approval',
                                   'protocol': 'docs/goal60-selection-protocol.md',
                                   'selected': results[0]['name'], 'candidates': results}, indent=2))
    for row in results:
        print(json.dumps({'name': row['name'], 'passing_pre_policy_signs': row['rank'][0],
                          'mean_recall_under_fp_cap': row['rank'][1],
                          'mean_healthy_correct_rate': row['rank'][2]}), flush=True)


if __name__ == '__main__':
    main()
