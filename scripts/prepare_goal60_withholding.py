"""Create an isolated experiment and empty reviewed-cohort templates."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.eval.confirmation_cohort import template
from ml.infer.validation_evidence import file_hash


def prepare(output):
    if output.exists():
        raise ValueError('Preserve existing experiments; choose another output directory')
    source = ROOT / 'data/raw/goal60_round2/selected_gpu.json'
    selected = json.loads(source.read_text())
    selected['validation_evidence'] = 'validation-evidence.json'
    selected['protocol'] = 'docs/goal60-withholding-protocol.md'
    for key, value in selected['models'].items():
        selected['models'][key] = str((source.parent / value).resolve())
    selected['locator'] = str((source.parent / selected['locator']).resolve())
    output.mkdir(parents=True)
    (output / 'development.json').write_text(json.dumps(selected, indent=2))
    (output / 'validation-evidence.json').write_text(json.dumps({'version': 1, 'records': []}, indent=2))
    for role in ('development', 'confirmation'):
        draft = template()
        draft['role'] = role
        (output / (role + '-cohort.template.json')).write_text(json.dumps(draft, indent=2))
    anchor = ROOT / 'ml/eval/goal60_round2_selected_gpu_valid.json'
    (output / 'status.json').write_text(json.dumps({'version': 1, 'deployment_approved': False,
        'validation_grants_issued': 0, 'reviewed_patients': 0,
        'reference_cache': str(anchor), 'reference_cache_sha256': file_hash(anchor),
        'reference_healthy_scan_false_alarms': {'outside': 6, 'healthy': 311},
        'external_dependencies': ['Qualified blinded sign review', 'Confirmed independent patient groups',
            'Permitted fresh paired-phone photos', 'Fresh confirmation after freezing']}, indent=2))
    print(json.dumps({'prepared': str(output), 'clinical_labels_created': 0, 'grants_issued': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'data/raw/goal60_withholding_round3')
    prepare(parser.parse_args().out)
