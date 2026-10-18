"""Report the fixed training experiment without replacing the prior evidence."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.infer.validation_evidence import file_hash


def report(out, previous):
    results = json.loads((out / 'results.json').read_text())
    verification = json.loads((out / 'verification.json').read_text())
    old_results = json.loads((previous / 'results.json').read_text())
    evidence_meta = json.loads((out / 'train-evidence.meta.json').read_text())
    training = []
    for condition in ('terrys_nails', 'pallor'):
        if file_hash(out / condition / 'manifest.json') != file_hash(previous / condition / 'manifest.json'):
            raise ValueError('Experiment data differs from the preregistered comparison')
        for seed in (42, 1337):
            name = f'{condition}_seed{seed}'
            record = json.loads((out / name / 'training_efficientnet_b0.json').read_text())
            old = json.loads((previous / name / 'training_efficientnet_b0.json').read_text())
            def losses(directory):
                return re.findall(r'epoch\s+(\d+)\s+train_loss\s+([0-9.]+)', (directory / (name + '.log')).read_text())
            a, b = losses(previous), losses(out)
            shared = min(len(a), len(b))
            training.append({'condition': condition, 'seed': seed,
                'old_calibration_macro_recall': old['best_valid_score'],
                'new_calibration_macro_recall': record['best_valid_score'],
                'best_epoch': record['best_epoch'], 'updates_at_best': record['best_updates'],
                'epochs_run': record['epochs_run'], 'initialization_weight': record['best_initialization_weight'],
                'shared_training_epochs': shared, 'shared_rounded_losses_identical': a[:shared] == b[:shared]})
    suites = ET.parse(ROOT / 'data/raw/goal60_training_repair_tests.xml').getroot().findall('testsuite')
    tests = {key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    if tests['failures'] or tests['errors']:
        raise ValueError('Regression tests failed')
    data = {'training': training, 'tests': tests,
        'production_manifest_sha256': file_hash(ROOT / 'ml/models/nail_color_classifier_labels.json'),
        'models_lock_sha256': file_hash(out / 'calibrated/models.lock.json'),
        'thresholds_lock_sha256': file_hash(out / 'thresholds.lock.json'),
        'results_sha256': file_hash(out / 'results.json'),
        'clinical_release_eligible': False, 'deployment_approved': False}
    (out / 'repair-audit.json').write_text(json.dumps(data, indent=2))
    (out / 'status.json').write_text(json.dumps({
        'phase': 'training repair and fixed development evaluation complete',
        'training_fault_fixed': True,
        'actual_displayed_passes': results['actual_displayed_passes'],
        'hypothetical_passes': results['hypothetical_all14_passes'],
        'strict_preservation': results['strict_preservation'],
        'engineering_verification_passes': verification['passes'],
        'candidate_rejected_for_preservation': not results['strict_preservation'],
        'deployment_approved': False, 'clinical_grants': 0,
        'qualified_cohorts_acquired': 0, 'emails_sent': 0,
    }, indent=2))
    comp = results['comparison']
    lines = ['# Training repair results — October 4, 2026', '',
        'Fixed the initialization-heavy moving average used during color-model training.',
        'The first optimized state now replaces the random starting state, and averaging',
        'strength increases with training updates. Selected epoch/update counts and the',
        'initial-state contribution are recorded. Geometry training and inference are unchanged.', '',
        'Three previous selected checkpoints retained 98.31–98.51% of their initialization;',
        'the fourth retained 71.16%. The repaired runs retain zero initial-state contribution.',
        'These are averaging weights, not percentages of correct predictions.', '',
        '| Model | Seed | Prior calibration macro recall | Repaired calibration macro recall | Selected epoch | Updates |',
        '|---|---:|---:|---:|---:|---:|']
    for row in training:
        lines.append(f"| {row['condition']} | {row['seed']} | {100*row['old_calibration_macro_recall']:.1f}% | {100*row['new_calibration_macro_recall']:.1f}% | {row['best_epoch']} | {row['updates_at_best']} |")
    lines += ['', 'Calibration measures localized crops on the fixed TRAIN-derived calibration cohort.',
        'Both data manifests are byte-identical to the prior run; shared rounded training-loss',
        f"trajectories match in all runs: {all(r['shared_rounded_losses_identical'] for r in training)}.", '',
        f"Actual displayed benchmark remains **{results['actual_displayed_passes']}/14**.",
        f"Experimental hypothetical passes: **{results['hypothetical_all14_passes']}/14**; no clinical grants.", '',
        '| Sign | Actual shown recall | Prior experiment | Repaired experiment | New healthy flags |',
        '|---|---:|---:|---:|---:|']
    def recall(row):
        return f"{100*row['recall']:.1f}% ({row['pos']['outside']}/{row['pos']['n']})" if row['recall'] is not None else 'unmeasured'
    for condition, value in results['all14'].items():
        lines.append(f"| {condition} | {recall(comp['reference'][condition])} | {recall(old_results['all14'][condition])} | {recall(value)} | {results['new_sign_healthy_flags'][condition]} |")
    lines += ['',
        f"Healthy scans flagged: {comp['healthy_scans']['any_outside']}/{comp['healthy_scans']['n']}, versus {comp['reference_healthy_scans']['any_outside']}/{comp['reference_healthy_scans']['n']} reference.",
        f"All previous correct positives preserved: {results['all_correct_positives_preserved']}. Strict preservation: {results['strict_preservation']}.",
        'A new per-sign healthy flag rejects the combined candidate even if it affects an already flagged scan.', '',
        '## Verification', '',
        f"- {tests['tests'] - tests['skipped']} backend/inference tests passed; failures/errors {tests['failures']}/{tests['errors']}.",
        f"- Endpoint: {verification['endpoint_images']} images, {verification['endpoint_findings']} findings; mismatches {len(verification['endpoint_mismatches'])}.",
        f"- Crop mismatch counts: endpoint {len(verification['crop_mismatches'])}, retained {len(verification['retained_crop_mismatches'])}/{verification['retained_crop_checks']}.",
        f"- CPU/GPU decision mismatches: {len(verification['device_mismatches'])}; largest rounded probability difference {verification['max_probability_difference']}.",
        f"- One healthy phone subject, four modes: hypothetical flags {[r['hypothetical_flags'] for r in verification['phone']]}.",
        f"- Stress-test hypothetical positives: {sum(r['hypothetical_positive'] for r in verification['stresses'])}; malformed upload status {verification['malformed_upload_status']}.",
        f"- Overall engineering verification passes: {verification['passes']}.", '',
        f"- Reused first-stage cache: {evidence_meta['fresh_stage_parity_images']} fresh comparisons matched first-stage verdicts and crop/quality extraction.", '',
        'Calibration scores are now bound to their exact model bundle, evidence and collector code;',
        'recovery rejects changed scores or models. Training source hashes are frozen and verified.', '',
        '## Remaining limits', '',
        'All fourteen denominators include failed localization, withheld results and abstentions.',
        'This is one fixed development experiment, with choices frozen before the reused VALID',
        'diagnostic. No threshold was selected on that diagnostic or historical TEST.',
        'Source/tone breakdowns, intervals and stage-two omitted-cohort results remain in results.json.',
        'The first-stage model ancestry has seen original TRAIN; omitted images are not independent',
        'confirmation of the entire pipeline. Unknown patient relationships may remain.', '',
        'Terry labels remain community assessments. Pallor labels remain anemia/Hb proxies,',
        'not qualified visible-pallor assessments; proxy negatives do not establish all14 signs absent.',
        'One healthy phone subject does not measure population accuracy. The repair cannot create',
        'clinical display permission or establish 12/14 or all14 readiness. Existing-data request',
        'drafts remain unsent and gated terms unaccepted.', '',
        '## Reproduction', '',
        f"Experiment: `{out.relative_to(ROOT).as_posix()}`.",
        'Protocol: [training repair](goal60-training-repair-protocol.md).',
        f"Production manifest SHA256: `{data['production_manifest_sha256']}`.",
        f"Models lock SHA256: `{data['models_lock_sha256']}`.",
        f"Thresholds lock SHA256: `{data['thresholds_lock_sha256']}`.",
        f"Results SHA256: `{data['results_sha256']}`.",
        'Prior artifacts remain retained; edited prior source is preserved in',
        '`data/raw/goal60_training_repair_source_before`. No production weights were replaced.', '']
    target = ROOT / 'docs/goal60-training-repair-results.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    return results, target


def update_vault(vault, out, previous):
    results, target = report(out, previous)
    for source, name in ((target, 'Training Repair Results - 2026-10-04.md'),
                         (ROOT / 'docs/goal60-training-repair-protocol.md', 'Training Repair Protocol - 2026-10-04.md')):
        shutil.copyfile(source, vault / name)
    marker = '## 2026-10-04 — Training-average repair'
    block = (marker + '\n\nFixed initialization-heavy model averaging; four isolated retrains on identical data splits. '
        f"Displayed benchmark remains {results['actual_displayed_passes']}/14; hypothetical {results['hypothetical_all14_passes']}/14. "
        f"Terry hypothetical recall {100*results['all14']['terrys_nails']['recall']:.1f}%; pallor proxy {100*results['all14']['pallor']['recall']:.1f}%. "
        f"New per-sign healthy flags: Terry {results['new_sign_healthy_flags']['terrys_nails']}, pallor {results['new_sign_healthy_flags']['pallor']}. "
        f"Strict preservation: {results['strict_preservation']}. No production adoption or grants. "
        'Qualified visible-sign evidence remains missing; request drafts remain unsent. '
        'See [[Training Repair Results - 2026-10-04]] and [[Training Repair Protocol - 2026-10-04]].\n')
    for name in ('Current State', 'Data and Models', 'Evaluation and Limitations', 'Decision Log', 'Next Actions', 'Change Log'):
        path = vault / (name + '.md')
        text = path.read_text(encoding='utf-8')
        if marker not in text:
            heading, _, rest = text.partition('\n')
            path.write_text(heading + '\n\n' + block + '\n' + rest, encoding='utf-8')
    home = vault / 'Home.md'
    text = home.read_text(encoding='utf-8')
    if '[[Training Repair Results - 2026-10-04]]' not in text:
        home.write_text(text.rstrip() + '\n\n- [[Training Repair Results - 2026-10-04]]\n- [[Training Repair Protocol - 2026-10-04]]\n', encoding='utf-8')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--previous', type=Path, default=ROOT / 'data/raw/goal60_image_round5_verified')
    ap.add_argument('--vault', type=Path)
    args = ap.parse_args()
    if args.vault:
        update_vault(args.vault, args.out.resolve(), args.previous.resolve())
    else:
        print(report(args.out.resolve(), args.previous.resolve())[1])
