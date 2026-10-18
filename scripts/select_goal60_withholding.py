"""VALID-only joint selection with a hard displayed healthy-scan budget."""
import argparse
import copy
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.routed_replay import replay
from ml.eval.withholding_checks import acceptance, PROTECTED, TARGETS
from ml.infer import validation_policy
from ml.infer.routing import RoutingRuntime, SHAPES, digest
from ml.infer.routing import rules_for
from ml.infer.validation_evidence import context, identity
from scripts.report_goal60 import CONDITIONS, score
from scripts.run_goal60_round2 import checked
from ml.eval.tune_color_decision import FLOORS, OVRS, SUPPORTS

UNLOCKS = tuple(c for c in TARGETS if c not in PROTECTED)


def displayed(record, condition, config, metadata, prospective):
    verdict, key = replay(record, condition, metadata, config)
    if key is None:
        return verdict, key
    if condition in SHAPES and not record.get('appearance_eligible', {}).get(condition):
        return record['findings'][condition].get('shown', verdict), key
    branch, model = record['branches'][key], metadata[config['model']]
    if condition in SHAPES:
        approved = (condition in model.get('validated_appearance_conditions', [])
                    and branch['mode'] in model.get('validated_roi_modes', []))
        if not approved and condition not in prospective:
            verdict = 'inconclusive'
    else:
        verdict = validation_policy.apply([{'label': condition, 'verdict': verdict}],
                    branch['mode'], model, approved=condition in prospective)[0]['verdict']
    return verdict, key


def options(condition, spec, metadata):
    initial = spec['conditions'][condition]
    yield initial
    if condition in PROTECTED or condition not in UNLOCKS:
        return
    for model, route in itertools.product(metadata, ('legacy', 'detector', 'detector_fallback')):
        if condition not in metadata[model].get('classes', []):
            continue
        yield {'model': model, 'route': route}
        if condition == 'terrys_nails':
            inherited = metadata[model].get('decision_rules', {}).get(condition, [.45, None, None])
            for values in itertools.product(FLOORS, OVRS, SUPPORTS):
                rules = [inherited[i] if value is None else value for i, value in enumerate(values)]
                yield {'model': model, 'route': route, 'rules': rules}
        elif condition == 'pallor' and model == 'pallor' and route == 'legacy':
            for floor in [round(.25 + i * .05, 2) for i in range(14)]:
                yield {'model': model, 'route': route, 'rules': [floor, None, .05]}


def joint_pick(tables, budget):
    """Exact dynamic program over unions of healthy false-alarm bitsets."""
    states = {0: ((0, 0.0, 0, 0), {})}
    for condition, candidates in tables.items():
        next_states = {}
        for mask, (value, picks) in states.items():
            for candidate in candidates:
                union = mask | candidate['healthy_mask']
                if union.bit_count() > budget:
                    continue
                rank = tuple(a + b for a, b in zip(value, candidate['rank']))
                if union not in next_states or rank > next_states[union][0]:
                    next_states[union] = (rank, {**picks, condition: candidate})
        states = next_states
        if not states:
            raise ValueError('No joint candidate preserves the healthy-scan budget')
    mask, (rank, picks) = max(states.items(), key=lambda item: (item[1][0], -item[0].bit_count()))
    return picks, mask.bit_count()


def permission_options(condition, requested):
    # Keeping current withholding is always an available development choice.
    return ((), (condition,)) if condition in requested else ((),)


def select(cache, manifest, reference_path, output, prospective=()):
    records = checked(cache, manifest)
    reference = json.loads(reference_path.read_text())
    initial = acceptance(records, reference, True)
    if not all(initial['protected'].values()):
        raise ValueError('Protected displayed outputs differ from the frozen anchor')
    spec = json.loads(manifest.read_text())
    runtime = RoutingRuntime(manifest)
    if runtime.validation.grants:
        raise ValueError('Joint development selection must precede confirmation grants')
    metadata = {key: model.metadata for key, model in runtime.models.items()}
    healthy = [r for r in records if r['labels'] == ['healthy']]
    anchor = score(reference, True)
    budget = acceptance(reference, reference)['healthy_scans']['any_outside']
    tables, diagnostics = {}, {}
    for condition in CONDITIONS:
        relevant = [r for r in records if condition in r['labels'] or r['labels'] == ['healthy']]
        candidates, seen = {}, set()
        for config, permissions in itertools.product(options(condition, spec, metadata), permission_options(condition, prospective)):
            token = json.dumps([config, permissions], sort_keys=True)
            if token in seen:
                continue
            seen.add(token)
            values = {r['path']: displayed(r, condition, config, metadata, permissions)[0] for r in relevant}
            positives = [values[r['path']] for r in relevant if condition in r['labels']]
            controls = [values[r['path']] for r in healthy]
            actual_values = values if not permissions else {r['path']: displayed(r, condition, config, metadata, ())[0] for r in relevant}
            actual_positives = [actual_values[r['path']] for r in relevant if condition in r['labels']]
            actual_controls = [actual_values[r['path']] for r in healthy]
            outside = controls.count('outside')
            recall = positives.count('outside') / len(positives) if positives else 0
            old = anchor[condition]
            if (outside > budget or outside / len(healthy) > .05
                    or controls.count('inconclusive') > old['healthy']['inconclusive']
                    or controls.count('within') < old['healthy']['within']
                    or positives.count('inconclusive') > old['pos']['inconclusive']):
                continue
            if (actual_controls.count('inconclusive') > old['healthy']['inconclusive']
                    or actual_controls.count('within') < old['healthy']['within']
                    or actual_positives.count('inconclusive') > old['pos']['inconclusive']):
                continue
            if condition in PROTECTED and config != spec['conditions'][condition]:
                continue
            mask = sum(1 << i for i, value in enumerate(controls) if value == 'outside')
            complexity = (int(config['route'] != 'legacy') + int('rules' in config)
                          + int(config['model'] != 'baseline') + int(bool(permissions)))
            rank = (int(condition in TARGETS and recall >= .6), recall if condition in TARGETS else 0,
                    controls.count('within'), -complexity)
            # Equal masks have identical effects on the joint FP constraint.
            candidate = {'config': config, 'healthy_mask': mask, 'rank': rank,
                         'recall': recall, 'healthy_fp': outside, 'proposed_permission': bool(permissions)}
            if mask not in candidates or rank > candidates[mask]['rank']:
                candidates[mask] = candidate
        if not candidates:
            raise ValueError(f'No coverage-preserving candidate for {condition}')
        tables[condition] = list(candidates.values())
        diagnostics[condition] = {'examined': len(seen), 'distinct_admissible_masks': len(candidates)}
        print(json.dumps({'condition': condition, **diagnostics[condition]}), flush=True)
    picks, count = joint_pick(tables, budget)
    selected_permissions = tuple(c for c in prospective if picks[c]['proposed_permission'])
    chosen = copy.deepcopy(spec)
    chosen['conditions'] = {c: picks[c]['config'] for c in CONDITIONS}
    chosen['deployment_approved'] = False
    chosen['validation_evidence'] = 'validation-evidence.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    # Relocation keeps model/locator references correct.
    for key, directory in chosen['models'].items():
        chosen['models'][key] = str((manifest.parent / directory).resolve())
    if chosen.get('locator'):
        chosen['locator'] = str((manifest.parent / chosen['locator']).resolve())
    registry = output.parent / 'validation-evidence.json'
    if registry.exists() and json.loads(registry.read_text()).get('records'):
        raise ValueError('Never overwrite existing validation grants')
    registry.write_text(json.dumps({'version': 1, 'records': []}, indent=2))
    def materialize(assumptions):
        result = []
        for record in records:
            findings = {}
            for condition in CONDITIONS:
                value, key = displayed(record, condition, chosen['conditions'][condition], metadata, assumptions)
                findings[condition] = {**record['findings'][condition], 'shown': value, 'route_id': key}
            result.append({**record, 'findings': findings})
        return result
    prospective_rows, actual_rows = materialize(selected_permissions), materialize(())
    if (not acceptance(prospective_rows, reference, True)['non_regression_passed']
            or not acceptance(actual_rows, reference, True)['non_regression_passed']):
        raise ValueError('Joint selection failed final displayed non-regression')
    output.write_text(json.dumps(chosen, indent=2))
    proposed_runtime = RoutingRuntime(output)
    contexts = {}
    for record in records:
        for condition in selected_permissions:
            finding = proposed_runtime.selected(record['branches'], condition)
            if finding.get('unvalidated_verdict') not in ('within', 'outside'):
                continue
            branch = record['branches'][finding['route_id']]
            config = proposed_runtime.spec['conditions'][condition]
            scope = context(proposed_runtime, condition, config, branch,
                rules_for(proposed_runtime.models[config['model']].metadata, condition, config.get('rules')),
                proposed_runtime.bundle_sha256)
            contexts[identity(scope)] = scope
    output.with_suffix('.contexts.json').write_text(json.dumps({'version': 1,
        'bundle_sha256': proposed_runtime.bundle_sha256, 'contexts': list(contexts.values()),
        'scope': 'Proposed from development only; not approval records'}, indent=2))
    result = {'version': 1, 'phase': 'development_selection', 'deployment_approved': False,
        'requested_hypothetical_unlocks': list(prospective),
        'hypothetical_unlocks': list(selected_permissions), 'validation_grants_issued': 0,
        'cache_sha256': digest(cache), 'reference_cache_sha256': digest(reference_path),
        'manifest_sha256': digest(output), 'healthy_scan_budget': budget,
        'prospective': acceptance(prospective_rows, reference, True),
        'actual_policy': acceptance(actual_rows, reference, True), 'diagnostics': diagnostics,
        'limitations': ['Prospective permissions are simulations, not issued grants',
                        'Development selection is not independent confirmation']}
    output.with_suffix('.selection.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'prospective_passing': result['prospective']['target_count'],
        'actual_passing': result['actual_policy']['target_count'], 'healthy_budget': budget,
        'prospective_healthy_flags': count, 'actual_non_regression': result['actual_policy']['non_regression_passed']}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--propose-unlocks', action='store_true', help='Research simulation only; registry remains empty')
    args = parser.parse_args()
    select(args.cache, args.manifest, args.reference, args.out, UNLOCKS if args.propose_unlocks else ())
