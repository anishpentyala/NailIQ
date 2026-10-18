"""Finish VALID selection, freeze one experiment, then run TEST and phone checks."""
import hashlib
import json
from pathlib import Path
import time

from scripts.run_goal60_candidates import EVAL, RAW, REPO, evaluate, finish, start
from scripts.report_goal60 import CONDITIONS, score


def job(name, script, arguments):
    finish(start(name, script, arguments), name)


def main():
    locator = RAW / 'goal60_nail_locator'
    specifications = []
    for model_name, model_dir, prefix in [
        ('MobileNet', RAW / 'goal60_authorized_mobilenet_frozen', 'goal60_mobilenet_roi_v2'),
        ('EfficientNet', RAW / 'goal60_authorized_efficientnet', 'goal60_authorized_efficientnet'),
        ('Ensemble', RAW / 'goal60_authorized_ensemble', 'goal60_authorized_ensemble'),
    ]:
        for mode in ['legacy', 'detector']:
            specifications.append({'name': f'{model_name} / {mode}',
                'model_dir': str(model_dir.relative_to(REPO)),
                'locator_dir': str(locator.relative_to(REPO)) if mode == 'detector' else None,
                'cache': str((EVAL / f'{prefix}_{mode}_valid.json').relative_to(REPO)),
                'rules': str((EVAL / f'{prefix}_{mode}_rules.json').relative_to(REPO))})
    spec = EVAL / 'goal60_final_candidate_spec.json'
    spec.write_text(json.dumps(specifications, indent=2))
    deadline = time.monotonic() + 2 * 3600
    for item in specifications:
        cache, rules = REPO / item['cache'], REPO / item['rules']
        while True:
            try:
                metadata = json.loads(cache.with_suffix('.meta.json').read_text())
                if metadata.get('split') == 'valid' and cache.is_file():
                    break
            except (OSError, ValueError):
                pass
            if time.monotonic() > deadline:
                raise RuntimeError(f"VALID evidence did not finish: {item['name']}")
            time.sleep(10)
        manifest = REPO / item['model_dir'] / 'nail_color_classifier_labels.json'
        existing = json.loads(rules.read_text()) if rules.is_file() else {}
        if (existing.get('valid_cache_sha256') != hashlib.sha256(cache.read_bytes()).hexdigest()
                or existing.get('candidate_manifest_sha256') != hashlib.sha256(manifest.read_bytes()).hexdigest()):
            job(rules.stem, 'ml/eval/tune_color_decision.py', ['--valid', cache, '--model-dir', manifest.parent,
                '--exclusions', RAW / 'goal60_exclusions_v3.json', '--min-recall', '0.60', '--out', rules])
    selection_path = EVAL / 'goal60_final_selection.json'
    job('goal60_final_selection', 'scripts/compare_goal60_candidates.py', ['--spec', spec, '--out', selection_path])
    selection = json.loads(selection_path.read_text())
    selected = selection['candidates'][0]
    frozen = RAW / 'goal60_selected_frozen_v3'
    arguments = ['--model-dir', REPO / selected['model_dir'], '--valid-cache', REPO / selected['cache'],
                 '--rules', REPO / selected['rules'], '--out', frozen]
    if selected['locator_dir']:
        arguments += ['--locator-dir', REPO / selected['locator_dir']]
    if selected['name'].startswith('Ensemble'):
        arguments += ['--lineage-dir', RAW / 'goal60_authorized_efficientnet']
    job('goal60_final_freeze', 'scripts/freeze_goal60_candidate.py', arguments)
    frozen_locator = frozen / 'locator' if selected['locator_dir'] else None
    valid_name = 'goal60_final_frozen_valid'
    finish(evaluate(valid_name, frozen, frozen_locator), valid_name)
    actual = score(json.loads((EVAL / f'{valid_name}.json').read_text()))
    for condition in CONDITIONS:
        for group in ['pos', 'healthy']:
            if actual[condition][group] != selected['conditions'][condition][group]:
                raise RuntimeError(f'Frozen rules differ from VALID replay: {condition}, {group}; TEST not run')
    print('Frozen VALID matches selection replay for all14; TEST starts now.', flush=True)
    common = ['--include-authorized', '--include-shapes', '--model-dir', frozen,
              '--exclusions', RAW / 'goal60_exclusions_v3.json']
    if frozen_locator:
        common += ['--locator-dir', frozen_locator]
    test_cache = EVAL / 'goal60_final_frozen_test.json'
    job('goal60_final_frozen_test', 'ml/eval/eval_end_to_end.py', ['--split', 'test', '--cache', test_cache, *common])
    phone_path = EVAL / 'goal60_final_frozen_phone.json'
    phone_args = ['--model-dir', frozen, '--out', phone_path]
    if frozen_locator:
        phone_args += ['--locator-dir', frozen_locator]
    job('goal60_final_frozen_phone', 'scripts/evaluate_goal60_phone.py', phone_args)
    test_report = EVAL / 'goal60_final_test_scorecard.json'
    job('goal60_final_test_scorecard', 'scripts/report_goal60.py', ['--cache', test_cache, '--out', test_report])
    job('goal60_final_write_results', 'scripts/write_goal60_results.py', [
        '--valid', EVAL / f'{valid_name}.json', '--test', test_cache, '--selection', selection_path,
        '--phone', phone_path, '--out', REPO / 'docs/goal60-results.md', '--plot', REPO / 'docs/goal60-test-recall.png'])
    print('All candidate checks complete; no weights deployed and no vault writes performed.', flush=True)


if __name__ == '__main__':
    main()
