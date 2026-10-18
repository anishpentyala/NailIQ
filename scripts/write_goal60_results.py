"""Write the complete frozen-candidate scorecard, including failed and withheld signs."""
import argparse
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.report_goal60 import CONDITIONS, report
from scripts.goal60_evidence import same_fingerprint

NAMES = {'clubbing': 'Clubbing appearance', 'koilonychia': 'Spoon-nail appearance',
         'beaus_lines': "Beau's lines", 'cyanosis': 'Cyanosis', 'leukonychia': 'Leukonychia',
         'lindsays_nails': "Lindsay's nails", 'melanonychia': 'Melanonychia',
         'muehrckes_lines': "Muehrcke's lines", 'onychogryphosis': 'Onychogryphosis',
         'onycholysis': 'Onycholysis', 'pallor': 'Pallor', 'pitting': 'Pitting',
         'splinter_hemorrhages': 'Splinter hemorrhages', 'terrys_nails': "Terry's nails"}


def fraction(successes, total, precision=1):
    return f'{successes / total:.{precision}%} ({successes}/{total})' if total else 'No samples'


def interval(bounds):
    return f'{bounds[0]:.1%}–{bounds[1]:.1%}' if bounds else 'No samples'


def plot_results(test, path):
    os.environ.setdefault('MPLCONFIGDIR', str(REPO / 'data/raw/goal60_plot_cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    conditions = list(reversed(CONDITIONS))
    rows = [test['conditions'][c]['pre_policy'] for c in conditions]
    x = [100 * (r['recall'] or 0) for r in rows]
    low = [max(0, v - 100 * r['recall_ci95'][0]) if r['recall_ci95'] else 0 for v, r in zip(x, rows)]
    high = [max(0, 100 * r['recall_ci95'][1] - v) if r['recall_ci95'] else 0 for v, r in zip(x, rows)]
    y = list(range(len(conditions)))
    fig, axis = plt.subplots(figsize=(12, 8.5))
    fig.subplots_adjust(left=0.28, right=0.82, top=0.87, bottom=0.22)
    axis.errorbar(x, y, xerr=[low, high], fmt='o', color='#21618c', capsize=3,
                  label='Before withholding; 95% interval')
    axis.scatter([100 * (test['conditions'][c]['recall'] or 0) for c in conditions], y,
                 marker='x', s=46, color='#b03a2e', label='What the experimental app shows', zorder=4)
    axis.axvline(60, color='#b9770e', linestyle='--', label='60% target')
    axis.set_yticks(y, [f"{NAMES[c]}  (n={r['pos']['n']})" for c, r in zip(conditions, rows)])
    axis.set_xlim(-2, 102)
    axis.set_xlabel('Strict positive detection recall (%) — abstentions count as misses')
    axis.set_title('Final held-out dataset results: all 14 scanned signs', loc='left', fontweight='bold', pad=25)
    axis.grid(axis='x', alpha=0.2)
    axis.spines[['top', 'right']].set_visible(False)
    for index, row in enumerate(rows):
        axis.text(1.03, index, fraction(row['healthy']['outside'], row['healthy']['n'], 2),
                  transform=axis.get_yaxis_transform(), va='center', fontsize=9,
                  color='#b03a2e' if (row['fp_rate'] or 0) > 0.05 else '#222222')
    axis.text(1.03, len(conditions) - 0.25, 'Healthy-label false alarms\nbefore withholding',
              transform=axis.get_yaxis_transform(), fontsize=9, fontweight='bold')
    fig.legend(*axis.get_legend_handles_labels(), loc='lower left',
               bbox_to_anchor=(0.28, 0.075), ncol=2, frameon=False, fontsize=9)
    fig.text(0.03, 0.025, 'Source-dataset labels and simulated framing; not clinical or phone accuracy.\n'
             'Shape rows measure appearance only. Small positive pools remain provisional. Production weights retained.',
             fontsize=9, color='#444444')
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['valid', 'test', 'selection', 'phone', 'out']:
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--plot', type=Path)
    args = parser.parse_args()
    valid, test = report(args.valid), report(args.test)
    phone, selection = json.loads(args.phone.read_text()), json.loads(args.selection.read_text())
    if valid['metadata'].get('split') != 'valid' or test['metadata'].get('split') != 'test':
        raise SystemExit('Both frozen VALID and final TEST evidence are required')
    if (not same_fingerprint(valid['metadata']['fingerprint'], test['metadata']['fingerprint'])
            or not same_fingerprint(test['metadata']['fingerprint'], phone['fingerprint'])):
        raise SystemExit('VALID, TEST and phone checks must use the same frozen code and weights')
    shown_pass = test['observed_target_met_for_all_14']
    pre_pass = [c for c in CONDITIONS if (test['conditions'][c]['pre_policy']['recall'] or 0) >= 0.6
                and test['conditions'][c]['pre_policy']['fp_rate'] is not None
                and test['conditions'][c]['pre_policy']['fp_rate'] <= 0.05]
    lines = ['# NailIQ all-14 candidate results', '',
             '**Target achieved:** ' + ('Yes, observed dataset point estimates only.' if shown_pass else 'No.'), '',
             f"Selected experiment: **{selection['selected']}**, using the fixed VALID-only selection protocol.",
             f"Final TEST pre-policy diagnostic: {len(pre_pass)}/14 signs meet recall >=60% and healthy FP <=5%.",
             'This diagnostic is before withholding unsupported findings. It is not deployed performance.', '',
             'All inconclusive positives and absent findings count as misses. Healthy false positives use every',
             'healthy image; the separate healthy correct rate also counts abstentions as failures.',
             'The benchmark uses source-dataset labels and simulated framing. It does not validate diagnoses,',
             'side-profile measurements or real phone performance. Shape rows concern top-photo appearance only.', '',
             '| Sign | Frozen VALID recall before policy | TEST recall before policy | TEST healthy FP before policy | TEST shown recall |',
             '|---|---:|---:|---:|---:|']
    for c in CONDITIONS:
        v, t, shown = valid['conditions'][c]['pre_policy'], test['conditions'][c]['pre_policy'], test['conditions'][c]
        warning = ' †' if t['pos']['n'] < 30 else ''
        lines.append(f"| {NAMES[c]}{warning} | {fraction(v['pos']['outside'], v['pos']['n'])} | "
                     f"{fraction(t['pos']['outside'], t['pos']['n'])} | "
                     f"{fraction(t['healthy']['outside'], t['healthy']['n'], 2)} | "
                     f"{fraction(shown['pos']['outside'], shown['pos']['n'])} |")
    lines += ['', '† Fewer than 30 TEST positives: provisional and particularly sensitive to individual photos.', '',
              'Terry\'s nails exceeds the healthy false-positive limit: 12/239 = 5.02%, not a rounded 5% pass.', '',
              '| Sign | TEST recall 95% interval before policy | Healthy correct rate before policy | Balanced accuracy before policy | Positive abstentions before policy | Healthy abstentions before policy |',
              '|---|---:|---:|---:|---:|---:|']
    for c in CONDITIONS:
        t = test['conditions'][c]['pre_policy']
        lines.append(f"| {NAMES[c]} | {interval(t['recall_ci95'])} | "
                     f"{fraction(t['healthy']['within'], t['healthy']['n'])} | "
                     f"{t['balanced_accuracy']:.1%} | "
                     f"{fraction(t['pos']['inconclusive'], t['pos']['n'])} | "
                     f"{fraction(t['healthy']['inconclusive'], t['healthy']['n'])} |")
    lines += ['', 'Candidate comparisons are pre-policy VALID diagnostics, not deployment approvals:', '',
              '| Automatic experiment | Signs passing both limits on VALID | Mean recall under FP cap | Mean healthy correct rate |',
              '|---|---:|---:|---:|']
    for row in selection['candidates']:
        rank = row['rank']
        lines.append(f"| {row['name']} | {rank[0]}/14 | {rank[1]:.1%} | {rank[2]:.1%} |")
    lines += ['', f"Healthy phone regression: **{'passed' if phone['passes'] else 'failed'}**, "
              f"{phone['subject_count']} existing subject; raw, guide-cropped and reviewer-assisted modes.",
              'The assisted boxes were reviewer-selected; this is not a user study or population benchmark.',
              'Production weights and existing validation/low-sample safeguards remain unchanged.', '',
              'The nail locator reached 91.3% box recall and 83.0% box precision on VALID at IoU >=0.5.',
              'Its first endpoint run regressed because focus was measured on a smooth tight interior rather',
              'than the classifier crop. The correction uses the same 15% padded crop and the unchanged focus',
              'threshold: 41/60 previously rejected VALID photos cleared it; 0/60 synthetically blurred versions did.',
              'Old failed runs are preserved. Annotation-box runs remain oracle diagnostics excluded from selection.', '',
              'A VALID-only guard audit found zero positive classical measurements for Lindsay\'s nails (0/6)',
              'and onycholysis (0/11) across legacy, detector and annotation-box routes. With the retained',
              'low-sample disagreement guard, no CNN-only retrain can produce a positive call on those same',
              'examples. Recovering them requires better validated measurements and independent evidence,',
              'rather than a lower CNN threshold. Audit: ml/eval/goal60_guard_recall_ceiling_valid.json.', '',
              'V3 quarantine excludes 73 crops, including three newly confirmed duplicate pairs. Known linked',
              'source families were excluded; complete cross-source patient/near-duplicate independence is not proven.',
              'Compatible initialization weights came from earlier isolated candidates; training was not from scratch.',
              'KNM and Arthitaya were included under explicit user-reported permission, without relabeling the Unknown',
              'public Arthitaya license. Runtime crops are additional views, not new independent subjects.', '',
              'Evidence artifacts:', '']
    for label, path in [('Frozen VALID', args.valid), ('Final TEST', args.test), ('Selection and per-source metrics', args.selection), ('Phone regression', args.phone)]:
        lines.append(f'- [{label}](<{path.resolve().as_posix()}>)')
    overall = test['healthy_scan_summary']
    lines += ['', 'Across all 14 findings, the final TEST healthy-label scan has:', '',
              f"- Any pre-policy outside finding: {fraction(overall['pre_policy']['any_outside'], overall['pre_policy']['n'])}.",
              f"- Any shown outside finding: {fraction(overall['shown']['any_outside'], overall['shown']['n'])}.",
              f"- All 14 pre-policy findings within: {fraction(overall['pre_policy']['all_within'], overall['pre_policy']['n'])}.",
              f"- Any pre-policy inconclusive finding: {fraction(overall['pre_policy']['any_inconclusive'], overall['pre_policy']['n'])}.",
              'These scan-level rates differ from each condition\'s false-positive rate; abstention is not a correct healthy call.']
    args.out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if args.plot:
        plot_results(test, args.plot)
        with args.out.open('a', encoding='utf-8') as output:
            output.write(f'\n![All-14 TEST recall and uncertainty](<{args.plot.resolve().as_posix()}>)\n')
    print(json.dumps({'report': str(args.out.resolve()), 'all_14_shown_target_met': shown_pass,
                      'test_pre_policy_passing_signs': pre_pass}), flush=True)


if __name__ == '__main__':
    main()
