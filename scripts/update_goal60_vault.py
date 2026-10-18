"""Append approved implementation and completed evaluation records to vault notes."""
import argparse
import json
from pathlib import Path

VAULT = Path(__file__).resolve().parents[2].parent / 'Obsidian Vaults/NailIQ'
MARKER = '## 2026-10-01 — Assisted ROI and appearance implementation'
COMMON = '''The user approved a dataset-first all-14 target: strict detection recall >=60%
with healthy false-positive rate <=5%, counting inconclusive positives as misses.
The goal is not achieved. Candidate weights remain isolated; crop-only numbers
do not validate the app, geometry measurements or phone performance.
'''
NOTES = {
    'Current State.md': COMMON + '''Normalized assisted nail boxes now flow through capture, validation and analysis.
The optional detector and top-photo shape fallback have separate validation gates.
Appearance findings contain no angle/depth measurement and do not override reliable
geometry. Production weights and low-sample guards remain unchanged.
203 ML/backend tests, frontend lint and build pass; mobile/desktop crop interactions
were checked. Candidate training and endpoint verification are still running.
''',
    'Data and Models.md': '''The user explicitly confirmed permission for KNM despite watermarks and separately
for Arthitaya. This is user-reported permission; documents were not inspected and
the Unknown public Arthitaya license was not relabeled CC BY.
The isolated dataset has 17 training classes; Mees' lines remains a discriminator.
Three new duplicate pairs (one conflicting pallor/melanonychia label) were visually
confirmed and both sides quarantined. V3 excludes 73 crops: TRAIN32/VALID30/TEST11.
The initial run was stopped; MobileNet restarted with v3, 23,184 TRAIN inputs
including 9,585 source-checked runtime crops and 1,480 VALID crops. Runtime crops
are not new subjects. EfficientNet and detector GPU jobs are serialized.
Artifacts: data/source_authorizations.json, data/raw/goal60_exclusions_v3.json,
data/raw/goal60_authorized_cls, data/raw/goal60_runtime_crops_v3.
''',
    'Evaluation and Limitations.md': COMMON + '''All-14 reporting now includes missing findings as misses, healthy correct rate,
balanced accuracy, abstentions and Wilson intervals. Tuner parity must pass before
VALID selection. Automatic ROI and annotation-box diagnostics are separate;
annotation boxes cannot establish actual user-crop accuracy.
Melanonychia has VALID3/TEST6 and Lindsay VALID6/TEST5 before further adjudication.
Point estimates on those pools cannot support a robust 60% claim. The known healthy
phone check remains one bootstrap subject, including reviewer-selected crops.
No new labeled phone cohort or paired side-geometry benchmark exists.
''',
    'Decision Log.md': '''The approved plan permits an optional user-adjusted nail crop and a top-photo
appearance fallback when side geometry is unreliable. Shape measurements stay
null; findings keep within/outside/inconclusive wording. The permission decision
for KNM and Arthitaya supersedes the earlier unresolved-source decision.
The plan retains all 14 conditions, the <=5% healthy FP limit, strict denominators,
low-sample abstention guards and separate phone/geometry evidence.
''',
    'Product and Design.md': '''Added translated nail-box review with pointer and keyboard movement/resizing,
confirmation and top-photo retake while preserving the side capture. Crop review
is advertised only after assisted-mode validation. Appearance evidence has its
own label and explanation that no side angle or depth was measured.
Responsive checks exercised 390x844, 375x667 and a desktop viewport; no horizontal
overflow was measured and crop coordinates/retake controls worked.
''',
    'Next Actions.md': '''KNM and Arthitaya permission decisions are resolved by explicit user statements.
Finish the v3 candidates, evaluate frozen models through /analyze on VALID, verify
tuner parity and select rules only there. Freeze the choice before TEST, report
all 14 including unsupported conditions, and run healthy-phone regression checks.
Reject unsafe or below-target candidates; no automatic production replacement or
commit. Rare-label adjudication and new independent phone/paired geometry data
remain evidence gaps rather than threshold problems.
''',
    'Change Log.md': COMMON + '''Implemented crop API/UI, optional nail detector training/inference, gated
appearance fallback, isolated authorized-data preparation, classifier-row-aligned
warm starts, source-matched specialist training support, all-14 scorecards and
strict missing-finding tuner denominators. Expanded duplicate quarantine to v3
and restarted training. Tests: 203 passed; lint/build and responsive crop checks pass.
Full results remain pending. See project docs/goal60-progress.md and isolated
candidate artifacts; no weights deployed and no commit created.
''',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, help='Completed all-14 Markdown scorecard')
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--test-report', type=Path)
    parser.add_argument('--phone', type=Path)
    parser.add_argument('--tests', type=int, default=215)
    args = parser.parse_args()
    if not (VAULT / 'Home.md').is_file():
        raise RuntimeError(f'Canonical vault missing: {VAULT}')
    if args.results:
        if not all([args.selection, args.test_report, args.phone]):
            parser.error('--results requires --selection, --test-report and --phone')
        selection = json.loads(args.selection.read_text())
        test = json.loads(args.test_report.read_text())
        phone = json.loads(args.phone.read_text())
        marker = '## 2026-10-02 — Frozen candidate final evaluation'
        summary = (f"The complete all-14 target remains {'met on observed dataset point estimates only' if test['observed_target_met_for_all_14'] else 'UNMET'}. "
                   f"VALID selected {selection['selected']}; weights/rules were frozen before TEST. "
                   'No production weight replacement, validation-guard relaxation or commit occurred.\n'
                   f"Verification: {args.tests} ML/backend tests pass; frontend lint/build and responsive crop checks pass. "
                   f"Healthy phone regression {'passed' if phone['passes'] else 'FAILED'} on one existing subject, "
                   'including reviewer-selected crops; this is not population accuracy.\n')
        final_notes = {
            'Current State.md': summary,
            'Data and Models.md': summary + 'Frozen experiments preserve source splits, v3 quarantine, earlier initialization provenance and source permission records.\n',
            'Evaluation and Limitations.md': args.results.read_text(encoding='utf-8'),
            'Next Actions.md': summary + 'Independent labeled full-frame positives for the remaining signs and paired side/phone evidence are still required. Preserve failed experiments; do not treat crop or oracle-box results as achieved app accuracy.\n',
            'Change Log.md': summary + 'Corrected the ROI focus check to use the classifier crop with the same threshold; froze VALID-selected evidence and reported all14 on TEST, including abstentions/healthy correct rates/intervals.\n',
        }
        for filename, body in final_notes.items():
            path = VAULT / filename
            text = path.read_text(encoding='utf-8')
            if marker not in text:
                path.write_text(text.rstrip() + '\n\n' + marker + '\n\n' + body, encoding='utf-8')
        print(f'Updated {len(final_notes)} result notes in {VAULT}')
        return
    for filename, body in NOTES.items():
        path = VAULT / filename
        text = path.read_text(encoding='utf-8')
        if MARKER not in text:
            path.write_text(text.rstrip() + '\n\n' + MARKER + '\n\n' + body, encoding='utf-8')
    print(f'Updated {len(NOTES)} authored notes in {VAULT}')


if __name__ == '__main__':
    main()
