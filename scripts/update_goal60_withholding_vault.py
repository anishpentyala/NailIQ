"""Append verified withholding implementation evidence to the canonical vault."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = '## 2026-10-03 — Withholding validation implementation'


def update(vault):
    folder = ROOT / 'data/raw/goal60_withholding_round3'
    status = json.loads((folder / 'status.json').read_text())
    selection = json.loads((folder / 'selected.selection.json').read_text())
    a, p = selection['actual_policy'], selection['prospective']
    common = (f"Local workflow implemented and verified: displayed {a['target_count']}/14; "
        f"simulated permissions {p['target_count']}/14. The 12 displayed and all-14 goals remain unmet. "
        f"Healthy scan false alarms {a['healthy_scans']['any_outside']}/311 versus frozen 6/311. "
        'No grants, new clinical labels, production adoption or outreach. '
        'See [[Withholding Results - 2026-10-03]] and [[Withholding Protocol - 2026-10-03]].\n')
    notes = {
        'Current State.md': common,
        'Data and Models.md': 'Added empty development/confirmation cohort templates and a reviewed specialist crop builder. '
            'Development patients require explicit TRAIN/VALID groups, source controls, rights references and reviewed '
            'present/absent sign labels. No confirmation data can enter training; no new reviewed cohort exists yet. '
            'Existing models were evaluated rather than retrained. Scoped identities include weights/calibration/classes, '
            'locator, routes/rules and relevant code.\n',
        'Evaluation and Limitations.md': common + '275 backend/inference tests pass. Full endpoint/replay: '
            '1350 VALID images/18900 findings, zero mismatches; CPU/GPU subset 64 images/896 findings, zero mismatches. '
            'Four-mode phone regression: one healthy subject/56 findings, zero device differences or false alarms. '
            'Frontend lint/build pass with existing bundle-size warning. VALID images use simulated framing, '
            'not independent patients or demonstrated phone sensitivity.\n',
        'Decision Log.md': 'User chose strict preservation and outside qualified review. The round-two displayed '
            '6/311 anchor replaces the older, looser aggregate baseline for this experiment. Freeze six protected signs; '
            'do not increase overall healthy-scan false alarms, per-sign abstentions, or reduce healthy correct results. '
            'Exact scoped grants require all independently confirmed gates; hypothetical permissions are not approvals. '
            'Withholding remains available per sign during joint selection. Reliable side geometry remains authoritative.\n',
        'Next Actions.md': common + 'Arrange qualified blinded review and permitted independent first paired phone captures. '
            'Evidence-gate defaults are 150 positives per sign and 400 healthy, possibly more for exact fallback/assisted '
            'branches. Improve weak routes on separate reviewed development patients; freeze scopes and candidate before '
            'one-use fresh confirmation. These counts are not a power calculation. All unsent access drafts remain unsent.\n',
        'Change Log.md': common + 'Added fail-closed scoped registry, strict shared healthy-FP-budget selection, '
            'patient/photo cohort isolation and confirmation lock/consumption ledger, complete paired endpoint comparisons, '
            'reviewed training-crop preparation, device/phone verification and relocatable frozen evidence. '
            'No safety switch was globally disabled. Source snapshot refreshed separately.\n',
    }
    for name in notes:
        if not (vault / name).is_file():
            raise ValueError('Canonical note missing: ' + name)
    for source, name in (
            ('docs/goal60-withholding-results.md', 'Withholding Results - 2026-10-03.md'),
            ('docs/goal60-withholding-protocol.md', 'Withholding Protocol - 2026-10-03.md'),
            ('docs/goal60-withholding-review-guide.md', 'Withholding Reviewer Guide - 2026-10-03.md')):
        (vault / name).write_bytes((ROOT / source).read_bytes())
    for name, body in notes.items():
        path = vault / name
        original = path.read_text(encoding='utf-8')
        if MARKER in original:
            continue
        block = MARKER + '\n\n' + body
        if name in ('Current State.md', 'Data and Models.md', 'Evaluation and Limitations.md', 'Next Actions.md'):
            title, _, rest = original.partition('\n')
            updated = title + '\n\n' + block + '\n' + rest
        else:
            updated = original.rstrip() + '\n\n' + block
        path.write_text(updated, encoding='utf-8')
    home = vault / 'Home.md'
    original = home.read_text(encoding='utf-8')
    if '[[Withholding Results - 2026-10-03]]' not in original:
        home.write_text(original.rstrip() + '\n\n- [[Withholding Results - 2026-10-03]]\n'
            '- [[Withholding Protocol - 2026-10-03]]\n- [[Withholding Reviewer Guide - 2026-10-03]]\n', encoding='utf-8')
    print(json.dumps({'vault': str(vault), 'notes_updated': 10, 'status': status['phase']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    update(parser.parse_args().vault)
