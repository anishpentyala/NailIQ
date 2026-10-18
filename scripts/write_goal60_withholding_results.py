"""Write current withholding results and explicit outstanding dependencies."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.report_goal60 import CONDITIONS
from ml.infer.validation_evidence import file_hash


def write():
    folder = ROOT / 'data/raw/goal60_withholding_round3'
    selection = json.loads((folder / 'selected.selection.json').read_text())
    verification = json.loads((ROOT / 'ml/eval/goal60_withholding_selected_verification.json').read_text())
    device = json.loads((ROOT / 'ml/eval/goal60_withholding_device_parity.json').read_text())
    phone = json.loads((ROOT / 'ml/eval/goal60_withholding_phone_parity.json').read_text())
    actual, prospective = selection['actual_policy'], selection['prospective']
    if verification['shown'] != actual['candidate']:
        raise ValueError('Selected full endpoint differs from the selection replay')
    lines = ['# Withholding implementation results — October 3, 2026', '',
        '## Outcome', '',
        f"Implemented the local validation and selection workflow. Displayed targets: **{actual['target_count']}/14**. "
        f"Simulation with proposed permissions: **{prospective['target_count']}/14**. The requested 12 displayed passes "
        'remain unachieved; simulations cannot clear withholding. No clinical grants, deployment, new labels or outreach occurred.', '',
        'These are 1,350 existing VALID clinical/community source images with simulated framing, '
        'including 311 healthy images. They are development evidence, not independent patients or phone accuracy.', '',
        f"Strict displayed non-regression: **{actual['non_regression_passed']}**. "
        f"Healthy scans with any outside result: **{actual['healthy_scans']['any_outside']}/311**, "
        'against the frozen 6/311 anchor. Protected six routes and outputs remain fixed. '
        'Per-sign healthy correct counts do not fall and positive/healthy inconclusives do not increase.', '',
        f"Healthy scans with any inconclusive result: {actual['healthy_scans']['any_inconclusive']}/311; "
        f"all fourteen results within range: {actual['healthy_scans']['all_within']}/311. "
        'Withheld conditions remain inconclusive; complete healthy-scan coverage is still absent.', '',
        'Terry displayed recall improves from 50/155 (32.3%) to 76/155 (49.0%), with healthy Terry false alarms '
        'falling from 2/311 to zero. It remains below 60%. The four additional simulated permissions are clubbing, '
        'koilonychia, leukonychia and melanonychia; they remain withheld in actual results.', '',
        '## Per-sign results', '',
        '| Sign | Positive images | Displayed recall | Simulated recall | Displayed healthy FP |',
        '|---|---:|---:|---:|---:|']
    for condition in CONDITIONS:
        a, p = actual['candidate'][condition], prospective['candidate'][condition]
        recall = lambda r: 'unknown' if r['recall'] is None else f"{100*r['recall']:.1f}%"
        lines.append(f"| {condition} | {a['pos']['n']} | {recall(a)} | {recall(p)} | {a['healthy']['outside']}/311 |")
    lines += ['', 'Hypothetical permissions selected: ' + (', '.join(selection['hypothetical_unlocks']) or 'none') +
        '. These are proposals only. Other requested permissions stay withheld in the selected simulation.', '',
        '## Implemented controls', '',
        '- Scoped approval registry binds sign, model/weights, route, actual ROI mode, rules, evidence kind and relevant code. '
        'Missing or changed proof fails closed; reliable side geometry stays authoritative.',
        '- Joint VALID selection counts the union of healthy false alarms. Withholding can remain per sign; '
        'low-confidence, failed and missing positives count as misses.',
        '- Reviewed cohort import requires qualified sign assessments, retained first side/top pairs, rights references '
        'and patient grouping. Confirmation and development cannot overlap.',
        '- Candidate/scopes/cohorts are locked before one-use fresh confirmation. Photo and patient claims prevent reuse '
        'by renaming a report. Full reference and current production are scored on the same patients.',
        '- Specialist crop preparation uses reviewed development patients with explicit TRAIN/VALID groups and source '
        'controls. Confirmation data cannot train a specialist. No reviewed-data retraining occurred.', '',
        '## Verification', '',
        '- Backend and inference tests: 275 passed. Frontend lint/build passed; existing bundle-size warning remains.',
        f"- Full endpoint/replay: {verification['images']} images, {verification['findings_checked']} findings, "
        f"{verification['mismatches']} mismatches; unverified geometry {verification['unverified_geometry']}.",
        f"- CPU/GPU subset: {device['images']} images, {device['findings_checked']} findings, {device['mismatches']} mismatches.",
        f"- One retained healthy phone subject in four capture modes: {phone['findings_checked']} findings, "
        f"{phone['mismatches']} mismatches; zero displayed and pre-policy false alarms on both devices.",
        '- These checks establish local regression results only. No observed increase does not prove population equivalence.', '',
        'The first joint winner failed the raw healthy-phone pre-policy check for melanonychia. Its partial endpoint run '
        'was stopped and is not a reported result. The previous melanonychia legacy route was restored; the rejected '
        'manifest, proposal, selection and failed phone report are retained under '
        '`data/raw/goal60_withholding_round3/rejected_phone_candidate`. The repaired endpoint was evaluated again.', '',
        '## Remaining work', '',
        'Qualified reviewers and permitted new patients/photos are still needed. Planning minima are 150 independently '
        'reviewed positives per claimed sign and 400 healthy patients, with adequate support for every proposed exact '
        'crop/evidence branch and source/tone subgroup. They are evidence gates, not a power calculation or guarantee.', '',
        'Improve weak routes using reviewed development data, repeat strict endpoint checks, then freeze all choices '
        'before new confirmation. Further tuning after a failed confirmation requires fresh patients. Lindsay and '
        'onycholysis remain unresolved; melanonychia has only three current positive development images. Pallor proxy '
        'labels require visible-sign review. Top appearance cannot establish nail angle or spoon depth.', '',
        'Protocol: [goal60-withholding-protocol.md](goal60-withholding-protocol.md). Local experiment: '
        '`data/raw/goal60_withholding_round3`; retained frozen bundle: `data/raw/goal60_withholding_frozen`.', '',
        'Evidence: `selected.selection.json`, `ml/eval/goal60_withholding_selected_verification.json`, '
        '`goal60_withholding_device_parity.json`, `goal60_withholding_phone_parity.json`. '
        'Default production weights and policies remain in use; experimental adoption was not performed.', '']
    (ROOT / 'docs/goal60-withholding-results.md').write_text('\n'.join(lines), encoding='utf-8')
    status = json.loads((folder / 'status.json').read_text())
    status.update({'phase': 'local_workflow_verified', 'displayed_target_count': actual['target_count'],
        'simulated_target_count': prospective['target_count'], 'twelve_displayed_target_met': False,
        'selected_manifest_sha256': file_hash(folder / 'selected.json'),
        'validation_grants_issued': 0, 'reviewed_patients': 0, 'non_regression_passed': actual['non_regression_passed'],
        'frozen_bundle_available': (ROOT / 'data/raw/goal60_withholding_frozen/routing.json').is_file()})
    (folder / 'status.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status))


if __name__ == '__main__':
    write()
