"""Write measured image-verifier outcomes and update the canonical project notes."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.infer.validation_evidence import file_hash


def report(out):
    results = json.loads((out / 'results.json').read_text())
    verification = json.loads((out / 'verification.json').read_text())
    comp = results['comparison']
    lines = ['# NailIQ image-verifier results — October 4, 2026', '',
        f"Displayed target on the retained selected-reference development benchmark: **{results['actual_displayed_passes']}/14**. Goal12 and all14 remain unproved.", '',
        'Completed four EfficientNet-B0 development runs, seeds42/1337 per sign,',
        'maximum20 epochs. Partial published-label crop/evaluation adapters and',
        'truthful side-view/Hb checks are implemented. No newly qualified source',
        'cohort was acquired, no release grants were written, and the app is unchanged.', '',
        f"Combined candidate rejected: Terry's nails {100*results['all14']['terrys_nails']['recall']:.1f}%, pallor proxy {100*results['all14']['pallor']['recall']:.1f}%; "
        f"pallor adds {results['new_sign_healthy_flags']['pallor']} per-sign healthy flag despite an unchanged scan union.", '',
        '| Sign | Actual shown recall | Hypothetical shown recall | Hypothetical healthy flags | Status |',
        '|---|---:|---:|---:|---|']
    for c, value in results['all14'].items():
        actual = comp['reference'][c]
        show = lambda r: f"{100*r['recall']:.1f}% ({r['pos']['outside']}/{r['pos']['n']})" if r['recall'] is not None else 'unmeasured'
        status = '>=60% observed' if value['recall'] is not None and value['recall'] >= .6 and value['fp_rate'] is not None and value['fp_rate'] <= .05 else 'target unmet'
        if c in ('pallor', 'terrys_nails'):
            status += '; shadow only, no display permission'
        lines.append(f"| {c} | {show(actual)} | {show(value)} | {value['healthy']['outside']}/{value['healthy']['n']} | {status} |")
    lines += ['', f"Hypothetical passes: {results['hypothetical_all14_passes']}/14; actual shown passes remain {results['actual_displayed_passes']}/14.",
        f"Healthy scans with any flag: {comp['healthy_scans']['any_outside']}/{comp['healthy_scans']['n']} hypothetical vs {comp['reference_healthy_scans']['any_outside']}/{comp['reference_healthy_scans']['n']} reference.",
        f"New healthy scan flags: {comp['paired_healthy']['new_flags']}. New per-sign healthy flags: {results['new_sign_healthy_flags']}. Strict preservation: {results['strict_preservation']}.", '',
        '## Verification', '',
        f"- Backend/inference verification: {json.loads((out / 'test-results.json').read_text())['passed']} tests passed.",
        f"- Fresh endpoint: {verification['endpoint_images']} images, {verification['endpoint_findings']} findings; {len(verification['endpoint_mismatches'])} mismatches.",
        f"- Crop comparisons: {len(verification['crop_mismatches'])} endpoint mismatches; {verification['retained_crop_checks']} retained training/calibration checks, {len(verification['retained_crop_mismatches'])} mismatches.",
        f"- New verifier CPU/GPU decisions: {len(verification['device_mismatches'])} mismatches; maximum rounded probability difference {verification['max_probability_difference']}.",
        f"- Existing healthy phone subject: one subject, four modes; hypothetical flags {[r['hypothetical_flags'] for r in verification['phone']]}. This is a bootstrap regression, not population evidence.",
        f"- Blur, dark lighting, glare, blank and invalid-image mutations: {sum(r['hypothetical_positive'] for r in verification['stresses'])} hypothetical positives.", '',
        '## Evidence limits and rejected outcomes', '',
        '- Available Terry labels are community assessments; pallor labels are anemia/Hb proxies.',
        '  Neither is newly independently qualified visible-sign ground truth.',
        '- Hb-normal proxy negatives cannot establish absence of Terry or all14 signs.',
        '  Healthy-FP results apply to the inherited development benchmark only.',
        '- TRAIN fit/calibration/omitted groups use known family IDs and exact image/crop',
        '  duplicates. Unknown patient relationships may remain. The first-stage model',
        '  ancestry has seen original TRAIN, so omitted cohorts only test the verifier.',
        '- Historical VALID is a reused development benchmark. Models, thresholds,',
        '  code and inputs were frozen before this diagnostic; no threshold was selected',
        '  on historical TEST or this new VALID comparison.',
        '- Inconclusive, missing and failed positive photos count as misses. Per-sign',
        '  recall/FP intervals, healthy correct/abstention counts, source/tone results',
        '  and omitted-cohort diagnostics are retained in results.json.',
        '- One original Terry calibration produced NaN; it is retained as unusable.',
        '  The separate finite bundle fits bounded temperature on the same TRAIN-derived',
        '  calibration using inference-matched horizontal flips. A pallor replica reaches',
        '  the temperature boundary, indicating weak discrimination; this is reported.',
        '- The cutoff writer stopped on a relative file path after all5122 images were',
        '  scored. Original image/label membership and weights were rechecked, and',
        '  retained TRAIN scores were used to finish freezing; no VALID choices changed.',
        '- Malformed uploads are tested through the API, which rejects them with',
        '  HTTP400. Well-formed encodings of non-image bytes remain invalid-image misses.',
        '- The shadow checker cannot create clinical grants. Improvements to two signs',
        '  do not approve clubbing, koilonychia, leukonychia or melanonychia display.',
        '- Lindsay and onycholysis remain explicitly reported, with their small original',
        '  positive counts. Unmeasured or withheld signs cannot disappear from the goal.', '',
        '## Existing-data requests', '',
        'Both [Terry request](goal60-terry-data-request.md) and',
        '[SEWA request](goal60-sewa-data-request.md) have verified published recipients.',
        'Requests remain UNSENT pending explicit sending approval. SEWA gated contact',
        'sharing and data-agreement acceptance are separately unapproved. No account',
        'details were submitted. No qualified local technician is needed for these requests.', '',
        '## Reproducibility and rollback', '',
        f"Experiment: {out.relative_to(ROOT).as_posix()}.",
        f"Models lock SHA256: {file_hash(out / 'calibrated/models.lock.json')}.",
        f"Thresholds lock SHA256: {file_hash(out / 'thresholds.lock.json')}.",
        f"Results SHA256: {file_hash(out / 'results.json')}.",
        'All original runs and rejected calibrations are retained. Production weights,',
        'public /analyze API and display gates were not edited. Stop referencing these',
        'isolated experiment files to roll back research use.', '',
        'See [implementation protocol](goal60-image-verifier-protocol.md).', '']
    target = ROOT / 'docs/goal60-image-verifier-results.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    inventory = {'checked_date': '2026-10-04', 'qualified_cohorts_acquired': 0,
        'terry_nelson': {'publication': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6025669/',
            'patient_count_in_paper': 503, 'reviewers': 'four physicians, independently blinded',
            'recipient': 'nnelson@alamedahealthsystem.org',
            'recipient_evidence': 'https://link.springer.com/article/10.1007/s11606-018-4441-7#author-information',
            'exact_consensus_positive_count': None, 'images_acquired': False,
            'reuse_permission': 'unconfirmed', 'request_status': 'prepared_unsent'},
        'sewa': {'dataset': 'https://huggingface.co/datasets/sewa-rural-care/anemia-survey-data',
            'recipient': 'sewarural@ymail.com', 'exact_visible_pallor_count': None,
            'assessor_qualifications': 'unverified', 'label_vocabulary': 'unverified',
            'images_acquired': False, 'gated_terms_accepted': False, 'account_details_shared': False,
            'request_status': 'prepared_unsent'},
        'existing_development': {'inventory': json.loads((out / 'inventory.json').read_text()),
            'qualified_visible_pallor': False, 'qualified_terry_reviews': False,
            'rights_reference': 'data/source_authorizations.json; private research scope only'}}
    (out / 'source-inventory.json').write_text(json.dumps(inventory, indent=2))
    return results, target


def vault_update(vault, out):
    results, target = report(out)
    comp = results['comparison']
    for source, name in ((target, 'Image Verifier Results - 2026-10-04.md'),
            (ROOT / 'docs/goal60-image-verifier-protocol.md', 'Image Verifier Protocol - 2026-10-04.md'),
            (ROOT / 'docs/goal60-terry-data-request.md', 'Terry Data Request - 2026-10-04.md'),
            (ROOT / 'docs/goal60-sewa-data-request.md', 'SEWA Data Request - 2026-10-04.md')):
        shutil.copyfile(source, vault / name)
    marker = '## 2026-10-04 — Image verifiers and published-label adapters'
    block = marker + '\n\n' + (
        f"Four isolated image-model runs completed. Displayed target {results['actual_displayed_passes']}/14; "
        f"hypothetical {results['hypothetical_all14_passes']}/14, no clinical permission. "
        f"Hypothetical healthy flags {comp['healthy_scans']['any_outside']}/311 vs4/311 reference; "
        f"strict preservation {results['strict_preservation']}. "
        f"Terry shadow {results['all14']['terrys_nails']['pos']['outside']}/155 ({100*results['all14']['terrys_nails']['recall']:.1f}%) with zero added healthy flags; "
        f"pallor shadow {results['all14']['pallor']['pos']['outside']}/338 ({100*results['all14']['pallor']['recall']:.1f}%) with one added per-sign flag. Combined candidate rejected. "
        'Partial published-label crops/evaluation implemented; side-photo availability never validates geometry, '
        'and Hb cannot become visible-pallor ground truth. Two data requests prepared with verified recipients, '
        'unsent pending explicit approval; gated terms/contact sharing remain unapproved. '
        'No qualified local technician required to request existing assessments. '
        'No newly qualified cohort, production adoption or clinical grants. '
        'Next: approved existing-data requests, then audit received labels/assessors/views/rights; no further tuning on reused VALID. '
        'See [[Image Verifier Results - 2026-10-04]] and [[Image Verifier Protocol - 2026-10-04]].\n')
    for name in ('Current State', 'Data and Models', 'Evaluation and Limitations', 'Decision Log',
                 'Next Actions', 'Change Log', 'People and Outreach'):
        path = vault / (name + '.md')
        text = path.read_text(encoding='utf-8')
        if marker in text:
            continue
        heading, _, rest = text.partition('\n')
        path.write_text(heading + '\n\n' + block + '\n' + rest, encoding='utf-8')
    home = vault / 'Home.md'
    text = home.read_text(encoding='utf-8')
    if '[[Image Verifier Results - 2026-10-04]]' not in text:
        home.write_text(text.rstrip() + '\n\n- [[Image Verifier Results - 2026-10-04]]\n'
            '- [[Image Verifier Protocol - 2026-10-04]]\n- [[SEWA Data Request - 2026-10-04]]\n', encoding='utf-8')
    print(json.dumps({'vault_updated': str(vault), 'actual_passes': results['actual_displayed_passes']}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--vault', type=Path)
    args = ap.parse_args()
    if args.vault:
        vault_update(args.vault, args.out.resolve())
    else:
        print(str(report(args.out.resolve())[1]))
