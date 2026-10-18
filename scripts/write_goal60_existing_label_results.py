"""Document frozen feature diagnostics and the existing expert-label alternative."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_goal60_feature_experiments import sha

OUT = ROOT / 'data/raw/goal60_feature_round4_verified'
MARKER = '## 2026-10-04 — Existing-label alternative and feature experiments'


def report():
    display = json.loads((OUT / 'display-preservation.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    features = json.loads((OUT / 'features.json').read_text())
    anchor_meta = json.loads((ROOT / 'ml/eval/goal60_withholding_selected_gpu_valid.meta.json').read_text())
    changed = [path for path, digest in anchor_meta['fingerprint'].items()
               if sha(Path(path)) != digest]
    if changed:
        raise ValueError('Original endpoint dependencies changed: ' + ', '.join(changed))
    lines = ['# Existing-label alternative: results — October 4, 2026', '',
        '**Displayed goal remains 6/14.** No production model/rule changes, clinical grants,',
        'new clinical labels, deployment or outreach occurred. The October 3 isolated',
        'reference remains 4/311 healthy scans flagged and Terry recall 76/155 (49.0%).',
        'A source-file/weight hash check confirms its endpoint dependencies are unchanged.', '',
        'The user cannot arrange qualified review. Implemented a research importer for',
        'already-published expert sign assessments, allowing partial labels and truthful',
        'top-only/unknown views without asking for new reviews. Unassessed signs stay',
        'unknown; anemia is not visible pallor; partial-negative records are not all-sign',
        'healthy cases. This importer does not write release grants.', '',
        '## Completed engineering experiment', '',
        'Processed 8,297 original full-image records: 6,947 TRAIN and 1,350 VALID.',
        'Automatic localization uses the same preprocessing, framing simulation, glare,',
        'polish and blur checks as the app. Failed localization remains in denominators.',
        'TRAIN group calibration selected forest depth and score threshold before VALID',
        'scoring. Two depths per sign plus two source-holdout models were trained (six total).',
        'Known source families/Ghana keys and exact-byte copies share calibration groups.',
        'No known TRAIN/VALID group or exact-byte overlap required additional quarantine.',
        'Existing exclusions retained; unknown patients/perceptual duplicates remain a limitation.', '',
        'Features include skin-relative redness, brightness-normalized longitudinal zones,',
        'saturation and proximal/distal white-band patterns. The inherited skin reference',
        'is an estimate, not verified skin segmentation. Forest vote fractions are not',
        'calibrated clinical probabilities. OpenCV minSampleCount=12 controls node splitting;',
        'the protocol phrase "minimum leaf sample count" is imprecise, not a leaf-size guarantee.', '',
        '## Proposed displayed rescues, before any permission', '',
        'These are hypothetical positive-only additions to the actual displayed reference,',
        '**not deployed app results**. Every option was fixed on TRAIN calibration.', '',
        '| Sign | TRAIN calibration FP budget | Proposed caught / positives | Recall | New healthy sign flags | Healthy scans flagged |',
        '|---|---:|---:|---:|---:|---:|']
    for c, title in (('terrys_nails', "Terry's nails"), ('pallor', 'Pallor proxy')):
        for key, row in display['conditions'][c].items():
            m = row['proposed_rescue']
            lines.append(f"| {title} | {float(key):.0%} | {m['tp']}/{m['positives']} | {m['recall']:.1%} | "
                         f"{row['new_sign_healthy_flags']} | {row['proposed_healthy_scans_any_outside']}/311 |")
    lines += ['', 'Terry reaches 60.6% only with ten new healthy flags; that challenger is rejected.',
        'The strict zero-new-flag Terry rescue adds one development hit (49.0% -> 49.7%).',
        'The 1% TRAIN-budget pallor challenger adds twelve hypothetical displayed proxy hits',
        '(3.6%) with zero new healthy flags, still far below target and unsupported as a',
        'visible-pallor finding. Small development gains do not justify production adoption.',
        'Protected six routes/decisions and all withholding policies remain unchanged.', '',
        'The original results.json and budget-results.json compare pre-policy predictions.',
        'Their pallor baseline134/338 is **hidden**, not displayed. Use display-preservation.json',
        'for the shown baseline0/338 and shared healthy-scan4/311 comparison. A regression',
        'test rejects using hidden "verdict" when the explicit "shown" field is unavailable.', '',
        '## Cross-source robustness', '',
        '| Research model | Entire omitted source | VALID caught / positives | Healthy flags |',
        '|---|---|---:|---:|']
    for c, item in result['source_holdout_diagnostics'].items():
        m = item['valid']
        lines.append(f"| {c} | {item['source']} | {m['tp']}/{m['positives']} | {m['fp']}/{m['healthy']} |")
    lines += ['', 'These source-held-out feature models separate the labels poorly. This is evidence',
        'against relying on these colour/spatial features alone; it is not evidence that',
        'a threshold change resolves withholding. Current VALID is reused development data,',
        'clinical/community images have simulated framing, and historical TEST was not used.',
        'No new independent clinical or phone sensitivity result is claimed.', '',
        '## Published-label work', '',
        '- SCIN public metadata audited: 5,033 cases, twenty self-reported nail cases.',
        '  Only two distinct cases mention exact target signs (leukonychia/Muehrcke in',
        '  one case, pitting in another). Differential possibilities cannot clear withholding.',
        '- SEWA Rural is an unverified possible pallor source. Local CSV/JSON/Parquet',
        '  schema/vocabulary auditing is ready. Gated access/contact sharing/terms acceptance',
        '  remain pending explicit authorization. No account information was submitted.',
        '- Nelson2018 photographed503 patients with four blinded physician Terry assessments.',
        '  No downloadable image/assessment cohort was found. An existing-data request is',
        '  prepared and **unsent**; acquisition and rights remain unconfirmed.', '',
        'See [source audit](goal60-published-label-audit.md), [unsent Terry request](goal60-terry-data-request.md),',
        '[engineering protocol](goal60-existing-label-protocol.md) and [budget protocol](goal60-feature-budget-protocol.md).', '',
        '## Verification and retained evidence', '',
        '- 286 backend/inference tests passed, including feature/vote, grouping, missing-data,',
        '  partial-label, duplicate-patient and hidden-versus-shown protections.',
        '- Frozen model/threshold and input hashes checked before scoring. Same1,350 VALID',
        '  image/label identities verified against the original endpoint cache.',
        '- No endpoint integration of challengers or new phone test was needed: none clears',
        '  both the target and preservation gate. Existing phone results remain bounded',
        '  one-subject evidence, not a fresh validation result.',
        '- Earlier feature caches are retained. Selection stopped on a stale bookkeeping',
        '  fingerprint; a later comparison stopped on Windows/POSIX path separators.',
        '  Rebuilt the final verified cache rather than altering previous frozen metadata.',
        '- Final experiment: data/raw/goal60_feature_round4_verified. Public-source audit:',
        '  data/raw/goal60_feature_round4/published-label-audit.json.', '',
        f"Model/threshold lock SHA256: `{sha(OUT / 'models.lock.json')}`.",
        f"Displayed comparison SHA256: `{sha(OUT / 'display-preservation.json')}`.", '',
        '## Next actions without recruiting a reviewer', '',
        'Pursue permitted access to already-assessed data and audit original sign-label',
        'vocabulary/provenance. The prepared importer accommodates those partial labels',
        'for research without inventing all-sign negatives or side views. Use eligible',
        'new sources to train a stronger image model and evaluate the actual endpoint.',
        'Published labels can substitute for commissioning review within their documented',
        'scope; they cannot establish unsupported views, all-sign healthy status or phone',
        'accuracy. No guarantee of12/14 or all14 follows from the current evidence.', '']
    (ROOT / 'docs/goal60-existing-label-results.md').write_text('\n'.join(lines), encoding='utf-8')
    status = {'phase': 'completed_research_experiment', 'displayed_passes': 6,
        'goal12_met': False, 'goal14_met': False, 'clinical_grants': 0, 'new_expert_sign_records': 0,
        'tests_passed': 286, 'endpoint_dependencies_unchanged': True,
        'healthy_anchor_any_outside': 4, 'train_images': 6947, 'valid_images': 1350,
        'sewa_access': 'authorization pending', 'outreach_sent': False,
        'models_lock_sha256': sha(OUT / 'models.lock.json'),
        'display_preservation_sha256': sha(OUT / 'display-preservation.json')}
    (OUT / 'status.json').write_text(json.dumps(status, indent=2))
    return status


def vault_update(vault):
    status = json.loads((OUT / 'status.json').read_text())
    common = ('Displayed target remains6/14; no release or clinical grants. Existing endpoint dependencies unchanged. '
        'Completed8,297-image feature experiment and286 tests. Terry reaches60.6% only with ten new healthy flags '
        '(rejected); zero-new-flag rescue49.7% remains below target. Pallor labels remain anemia proxies. '
        'See [[Existing Label Results - 2026-10-04]].\n')
    notes = {'Current State.md': common,
        'Data and Models.md': common + 'Research importer accepts already-published expert partial sign labels with '
            'qualification/source/rights references and documented patient grouping. Missing signs stay unknown. '
            'SCIN has only two relevant differential cases; SEWA access/label qualification unverified.\n',
        'Evaluation and Limitations.md': common + 'No historical TEST or new phone sensitivity evaluation. '
            'Feature models and eight TRAIN-selected budget choices remained isolated; source-held-out models were weak. '
            'Actual shown comparison separates hidden predictions from displayed verdicts.\n',
        'Decision Log.md': 'User cannot arrange qualified review and chose an existing-label alternative. '
            'Do not make personal clinician recruitment the immediate dependency. Reuse original published expert '
            'assessments only within their actual sign/view/rights scope; no disease/Hb-to-visible-sign conversion, '
            'invented negative labels or automatic clinical grants. Rejected Terry threshold that introduces ten healthy flags.\n',
        'Next Actions.md': common + 'Supersedes clinician-recruitment-first instructions in older dated entries: '
            'pursue permitted already-assessed datasets. SEWA contact/terms permission request pending; '
            'Terry503-patient existing-assessment request prepared but unsent. Import acquired eligible labels, '
            'then train/evaluate stronger models without relaxing current safeguards.\n',
        'Change Log.md': common + 'Added metadata-only public-label audit, partial published-label importer/template, '
            'colour/spatial feature challengers, source holdouts, frozen budget diagnostics and shown-preservation checks. '
            'No gated data downloaded or outreach sent. Source archive sync recorded separately.\n'}
    for name in notes:
        if not (vault / name).is_file():
            raise ValueError('Canonical note missing: ' + name)
    for filename, title in (('goal60-existing-label-results', 'Existing Label Results'),
            ('goal60-published-label-audit', 'Published Label Audit'), ('goal60-terry-data-request', 'Terry Data Request')):
        (vault / f'{title} - 2026-10-04.md').write_bytes((ROOT / 'docs' / (filename + '.md')).read_bytes())
    for name, text in notes.items():
        path = vault / name
        original = path.read_text(encoding='utf-8')
        if MARKER in original:
            continue
        block = MARKER + '\n\n' + text
        if name in ('Current State.md', 'Data and Models.md', 'Evaluation and Limitations.md', 'Next Actions.md'):
            heading, _, rest = original.partition('\n')
            original = heading + '\n\n' + block + '\n' + rest
        else:
            original = original.rstrip() + '\n\n' + block
        path.write_text(original, encoding='utf-8')
    home = vault / 'Home.md'
    text = home.read_text(encoding='utf-8')
    if '[[Existing Label Results - 2026-10-04]]' not in text:
        home.write_text(text.rstrip() + '\n\n- [[Existing Label Results - 2026-10-04]]\n'
            '- [[Published Label Audit - 2026-10-04]]\n- [[Terry Data Request - 2026-10-04]]\n', encoding='utf-8')
    print(json.dumps({'vault': str(vault), 'phase': status['phase']}))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path)
    args = parser.parse_args()
    if args.vault:
        vault_update(args.vault)
    else:
        print(json.dumps(report()))
