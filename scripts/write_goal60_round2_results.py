"""Render measured development results, preserving all 14 signs and withholding."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NAMES = {'clubbing': 'Clubbing appearance', 'koilonychia': 'Spoon-nail appearance',
         'leukonychia': 'Leukonychia', 'melanonychia': 'Melanonychia', 'pallor': 'Pallor proxy',
         'cyanosis': 'Cyanosis', 'terrys_nails': "Terry's nails", 'lindsays_nails': "Lindsay's nails",
         'onycholysis': 'Onycholysis', 'beaus_lines': "Beau's lines", 'muehrckes_lines': "Muehrcke's lines",
         'splinter_hemorrhages': 'Splinter hemorrhages', 'pitting': 'Pitting', 'onychogryphosis': 'Onychogryphosis'}


def read(path):
    return json.loads((REPO/path).read_text())


def percentage(value):
    return 'unmeasured' if value is None else f'{value*100:.1f}%'


def fraction(group, key='outside'):
    return f'{percentage(group[key]/group["n"] if group["n"] else None)} ({group[key]}/{group["n"]})'


def main():
    result = read('ml/eval/goal60_round2_selected_verification.json')
    selection = read('data/raw/goal60_round2/selected_gpu.selection.json')
    routing = read('data/raw/goal60_round2/selected_gpu.json')
    device = read('ml/eval/goal60_round2_device_parity.json')
    phone = read('ml/eval/goal60_round2_phone_parity.json')
    training = read('data/raw/goal60_round2_pallor/training_efficientnet_b0.json')
    frozen = read('data/raw/goal60_round2_frozen/lineage.json')
    passes = lambda row: row['recall'] is not None and row['recall'] >= .6 and row['fp_rate'] is not None and row['fp_rate'] <= .05
    diagnostic = sum(passes(row) for row in result['pre_policy'].values())
    shown = sum(passes(row) for row in result['shown'].values())
    lines = ['# NailIQ round-two development results', '', '**All-14 goal achieved: No.**', '',
        f'Completed October 3, 2026 under the October 2 approved protocol. Current VALID endpoint evidence: '
        f'{result["images"]} full source images, including 311 healthy images. Before-policy diagnostics '
        f'meet the observed 60% recall / <=5% healthy-FP target for {diagnostic}/14 signs; shown findings '
        f'for {shown}/14. These are development results, not new independent clinical confirmation.', '',
        'All positive abstentions and missing findings count as misses. FP uses all healthy images; '
        'healthy correct and abstention rates are reported separately. No historical TEST was selected '
        'or evaluated this round. Production weights and policy safeguards remain unchanged.', '',
        'Minority-class counts remain small: melanonychia3, leukonychia11, Lindsay6 and onycholysis11 '
        'development positives. Their point estimates are provisional. Source/community labels and '
        'simulated framing do not establish patient-independent phone or clinical accuracy.', '',
        '| Sign | Baseline recall | Selected recall before policy | Healthy FP | Shown recall | Selected route/model |',
        '|---|---:|---:|---:|---:|---|']
    for c, row in result['pre_policy'].items():
        config = routing['conditions'][c]
        lines.append(f'| {NAMES[c]} | {fraction(result["common_baseline"][c]["pos"])} | '
                     f'{fraction(row["pos"])} | {fraction(row["healthy"])} | {fraction(result["shown"][c]["pos"])} | '
                     f'{config["route"]} / {config["model"]} |')
    lines += ['', '| Sign | Positive abstentions | Healthy correct | Healthy abstentions | Recall 95% interval |',
              '|---|---:|---:|---:|---:|']
    for c, row in result['pre_policy'].items():
        interval = row.get('recall_ci95')
        ci = 'unmeasured' if not interval else '–'.join(percentage(v) for v in interval)
        lines.append(f'| {NAMES[c]} | {fraction(row["pos"], "inconclusive")} | '
                     f'{fraction(row["healthy"], "within")} | {fraction(row["healthy"], "inconclusive")} | {ci} |')
    lines += ['', '## What changed and what was rejected', '']
    for c, row in selection['conditions'].items():
        picked = row['selected']
        if picked['config'] != {'model': 'baseline', 'route': 'legacy'}:
            lines.append(f'- {NAMES[c]}: selected `{json.dumps(picked["config"], sort_keys=True)}`. '
                         f'Recall {percentage(row["baseline"]["recall"])} → {percentage(picked["metrics"]["recall"])}; '
                         f'healthy FP {percentage(row["baseline"]["fp_rate"])} → {percentage(picked["metrics"]["fp_rate"])}.')
    lines += ['- Six previously passing signs remain frozen EfficientNet/legacy. Detector-first fallback uses '
              'the complete legacy branch only for pre-policy failure/inconclusive; policy withholding cannot trigger fallback.',
              '- Candidates violating FP or healthy-coverage limits were rejected. Extra healthy abstention may '
              'not exceed FP reduction+2 percentage points against the common baseline. Terry development FP cap is3%.',
              '- Reliable side geometry remains authoritative. Top-photo shape findings carry no angle/depth. '
              'Clinical full images with simulated framing do not validate paired side measurements.',
              '- Low-sample disagreement guards remain. Offline Lindsay zone and onycholysis area measurements '
              'have synthetic tests but no newly adjudicated clinical evidence; they were not integrated.', '',
              'The new detector ROI has not been cleared by the existing display policy. Terry shown recall '
              'falls to32.3% (50/155), despite92.3% before-policy recall. Appearance, pallor and other '
              'unsupported findings stay withheld. This is a research candidate, not a deployable improvement '
              'to user-visible performance. No policy was relaxed to make the numbers pass.', '',
              '## Verification and training lineage', '',
              f'- Endpoint/replay: {result["findings_checked"]} findings, {result["mismatches"]} shown/pre-policy/route mismatches. '
              f'Frozen-v3 baseline regression: {result["historical_baseline_comparison"]["mismatches"]} mismatches. '
              'All per-sign coverage constraints pass.',
              f'- CPU/GPU regression: {device["images"]} frames, {device["findings_checked"]} findings, '
              f'{device["mismatches"]} exact verdict/route mismatches. Maximum rounded-probability difference '
              f'{device["maximum_rounded_probability_delta"]:.6f}; maximum normalized-bbox difference '
              f'{device["maximum_normalized_bbox_delta"]:.8f}. This is bounded device regression, not a full CPU population benchmark.',
              f'- Healthy-phone regression: one existing subject, four modes on each device; '
              f'{phone["mismatches"]} device mismatches. Shown/pre-policy zero-false-alarm gates: '
              f'{phone["passes_shown"]}/{phone["passes_pre_policy"]}. Assisted boxes were reviewer selected.',
              f'- Pallor specialist: EfficientNet, seed42, {training["epochs_run"]}/20 maximum epochs with early stopping. '
              f'Best crop macro recall {percentage(training["best_valid_score"])}; temperature1.0074. '
              'TRAIN Ghana healthy1383/pallor2050; crop VALID healthy186/pallor233. Four ambiguous `Anmeic` '
              'crop labels are excluded from the frozen full-image label parser; Ghana endpoint positives229. '
              'Labels are anemia proxies, not independent visible-pallor judgments.',
              '- Exact input hashes, source counts and initializer records are retained. Initialization descends '
              'from earlier candidates; source matching applies to this fine-tuning stage, not all weight ancestry. '
              'Patient independence remains unproven.',
              '- ML/backend236 tests pass. Frontend lint and build pass. Earlier partial CPU runs stopped '
              'during code review were discarded. The isolated GPU environment and disabled TF32 are recorded in cache metadata.',
              f'- Freeze binds models by model ID, manifests, weights, lineage, cache, parity and verification '
              f'(verification SHA256 `{frozen["verification_sha256"]}`). It is experimental and deployment is not approved.', '',
              '## Healthy scans and source breakdown', '']
    for mode, row in result['healthy_scans'].items():
        lines.append(f'- {mode}: any outside {row["any_outside"]}/{row["n"]} '
                     f'({percentage(row["any_outside_rate"])}); all within {row["all_within"]}/{row["n"]}; '
                     f'any inconclusive {row["any_inconclusive"]}/{row["n"]}.')
    lines += ['', '| Source | Pallor caught | Healthy pallor FP | Terry caught | Healthy Terry FP |',
              '|---|---:|---:|---:|---:|']
    for source, rows in result['by_source'].items():
        lines.append(f'| {source} | {fraction(rows["pallor"]["pos"])} | {fraction(rows["pallor"]["healthy"])} | '
                     f'{fraction(rows["terrys_nails"]["pos"])} | {fraction(rows["terrys_nails"]["healthy"])} |')
    lines += ['', '## Remaining dependency and artifacts', '',
              'The local annotation index covers9998 TRAIN/VALID images with zero new clinical labels. '
              'Repeated photos are not independent patients. Five corrected access drafts are unsent. '
              'No clinician is arranged or new dataset acquired. Arrange qualified sign adjudication, grouping '
              'and permitted fresh paired-phone collection before asserting improved clinical performance. '
              'Planning targets150 positive patients/sign and400 healthy are not performance guarantees.', '',
              '- [Clinical packets and unsent requests](goal60-round2-clinical-packet.md)',
              '- [Approved protocol](goal60-round2-protocol.md)',
              '- Development/selection: `ml/eval/goal60_round2_development_gpu_valid.*`, '
              '`data/raw/goal60_round2/selected_gpu.selection.json`',
              '- Accepted endpoint/parity: `ml/eval/goal60_round2_selected_gpu_valid.*`, '
              '`ml/eval/goal60_round2_selected_verification.json`',
              '- Device/phone: `ml/eval/goal60_round2_device_parity.*`, `ml/eval/goal60_round2_phone_parity.json`',
              '- Frozen candidate: `data/raw/goal60_round2_frozen/routing.json` and `lineage.json`',
              '- Review packets: `data/raw/goal60_round2_review`; specialist: `data/raw/goal60_round2_pallor`', '']
    (REPO/'docs/goal60-round2-results.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'diagnostic_passing': diagnostic, 'shown_passing': shown, 'all_14_goal_met': False}))


if __name__ == '__main__':
    main()
