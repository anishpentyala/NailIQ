"""Append measured round-two results without rewriting historical vault notes."""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKER = '## 2026-10-03 — Round-two development results'


def update(vault):
    result = json.loads((REPO/'ml/eval/goal60_round2_selected_verification.json').read_text())
    selection = json.loads((REPO/'data/raw/goal60_round2/selected_gpu.selection.json').read_text())
    parity = json.loads((REPO/'ml/eval/goal60_round2_device_parity.json').read_text())
    phone = json.loads((REPO/'ml/eval/goal60_round2_phone_parity.json').read_text())
    report = (REPO/'docs/goal60-round2-results.md').read_text(encoding='utf-8')
    clinical = (REPO/'docs/goal60-round2-clinical-packet.md').read_text(encoding='utf-8')
    changed = [c for c, row in selection['conditions'].items()
               if row['selected']['config'] != {'model': 'baseline', 'route': 'legacy'}]
    common = ('The approved local experiment is complete; the all-14 goal remains unmet. '
              'Results use current TRAIN/VALID development data, not fresh clinical confirmation. '
              'Production weights were not replaced and no deployment or outreach occurred. '
              'See [[Round Two Results - 2026-10-03]].\n')
    notes = {
        'Current State.md': common + f'Conditions changed in the isolated candidate: {", ".join(changed) or "none"}. '
            'Before-policy development targets pass12/14; shown findings6/14. Terry shown recall falls '
            'to32.3% because detector ROI is not display-validated, so no user-visible improvement is deployed. '
            'Per-sign model/ROI routing uses immutable rules, complete legacy fallback on pre-policy '
            'failure only, assisted priority and unchanged low-sample guards. Reliable geometry remains authoritative.\n',
        'Data and Models.md': 'One Ghana source-matched binary EfficientNet pallor specialist completed 15 epochs '
            '(20 maximum, early stopping), seed42; best crop VALID macro recall84.9%, temperature1.0074. '
            'Exact lineage: TRAIN healthy1383/pallor2050; VALID healthy186/pallor233. Anemia proxy labels '
            'are not adjudicated visible pallor. Warm-start ancestry includes prior candidates; no TEST '
            'evaluation was run this round. Local review index:9998 TRAIN/VALID image references, zero '
            'new clinical labels; repeated appearances require patient grouping. Four ambiguous Anmeic '
            'crop labels explain233 crop-VALID versus229 full-image Ghana positives; review pending.\n',
        'Evaluation and Limitations.md': common + f'Full endpoint/replay check: {result["images"]} images, '
            f'{result["findings_checked"]} findings; {result["mismatches"]} mismatches. Current images, labels, '
            'membership, exclusions, rules and weights are bound by hashes. '
            f'Device regression:{parity["images"]} frames/{parity["mismatches"]} mismatches; '
            f'four-mode phone CPU/GPU regression:{phone["mismatches"]} mismatches on one existing healthy subject. '
            'These do not establish patient-independent phone accuracy or side-geometry accuracy.\n',
        'Decision Log.md': 'Six previously passing signs remain frozen EfficientNet/legacy. All candidates '
            'share that healthy-coverage baseline: additional abstention must not exceed FP reduction+2pp. '
            'Terry development FP cap3%; pallor binary output affects only pallor. Missing models or '
            'detector proposals cannot fabricate valid evidence. No clinical safeguard was removed.\n',
        'Next Actions.md': common + 'Arrange qualified sign review, confirm duplicate/patient groups and '
            'adjudicate the local packets. Acquire permitted independent patients and paired phone views; '
            'planning target150 positives/sign and400 healthy is not a performance guarantee. Freeze final '
            'choices before fresh confirmation. Historical TEST cannot serve as a new confirmation set.\n',
        'People and Outreach.md': 'Five unsent data-access drafts are in [[Clinical Packet - 2026-10-03]]: '
            'FAU, Lindsay study, Cornell, Lam lab and UNSM follow-up. FAU masks/leukonychia labels, '
            'Lindsay/Cornell photo inventories and all raw-image reuse terms remain unconfirmed. '
            'The vault records the prior September17 UNSM request; no email reply check was performed '
            'this round. Balearic private-company images are excluded from the request shortlist.\n',
        'Change Log.md': common + 'Added experimental routing, complete branch caches/replay, strict '
            'current-input checks, model-ID freeze lineage, source reporting and device/phone verification. '
            'Added reviewed-mask measurement prototypes and clinical packets; they do not emit diagnoses '
            'or production verdicts. ML/backend:236 tests pass; frontend lint/build pass. '
            'CPU partial runs stopped during code review were discarded, not reported as results.\n'}
    for name in notes:
        if not (vault/name).is_file():
            raise ValueError(f'Canonical note missing: {name}')
    (vault/'Round Two Results - 2026-10-03.md').write_text(report, encoding='utf-8')
    (vault/'Clinical Packet - 2026-10-03.md').write_text(clinical, encoding='utf-8')
    for name, body in notes.items():
        path = vault/name
        original = path.read_text(encoding='utf-8')
        if MARKER not in original:
            block = MARKER+'\n\n'+body
            if name in {'Current State.md', 'Data and Models.md', 'Evaluation and Limitations.md', 'Next Actions.md'}:
                title, _, rest = original.partition('\n')
                updated = title+'\n\n'+block+'\n'+rest
            else:
                updated = original.rstrip()+'\n\n'+block
            path.write_text(updated, encoding='utf-8')
    home = vault/'Home.md'
    original = home.read_text(encoding='utf-8')
    if '[[Round Two Results - 2026-10-03]]' not in original:
        home.write_text(original.rstrip()+'\n\n- [[Round Two Results - 2026-10-03]]\n- [[Clinical Packet - 2026-10-03]]\n', encoding='utf-8')
    print(json.dumps({'vault': str(vault), 'notes': len(notes)+3, 'goal_achieved': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    update(parser.parse_args().vault)
