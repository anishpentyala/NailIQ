"""Record reconstructed exact fine-tuning inputs and inherited initialization evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.train import train_color_classifier as trainer


def main():
    directory = REPO / 'data/raw/goal60_round2_pallor'
    training = json.loads((directory/'training_efficientnet_b0.json').read_text())
    exclusion_path = REPO/'data/raw/goal60_exclusions_v3.json'
    assert hashlib.sha256(exclusion_path.read_bytes()).hexdigest() == training['exclusions_sha256']
    trainer.DATA_DIR = Path(training['data_dir'])
    exclusions = json.loads(exclusion_path.read_text())
    rows = []
    for split in ('train','valid'):
        dataset = trainer.CropDataset(training['classes'], split, False, exclusions=exclusions)
        for path, label in dataset.samples:
            source = path.name.split('__',1)[0]
            if source not in training['matched_sources']:
                continue
            rows.append({'path': path.relative_to(REPO).as_posix(), 'split': split, 'label': training['classes'][label],
                         'source': source, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'patient_group': None, 'patient_group_status': 'not reconstructed; original grouped source splits retained'})
    init_dir = REPO/'data/raw/goal60_selected_frozen_v3'
    sources = [init_dir/'nail_color_classifier_labels.json'] + sorted((init_dir/'lineage').glob('*.json'))
    result = {'rows': rows, 'counts': dict(Counter((r['split']+'/'+r['source']+'/'+r['label']) for r in rows)),
              'training_metadata_sha256': hashlib.sha256((directory/'training_efficientnet_b0.json').read_bytes()).hexdigest(),
              'initialization_records': {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              'source_matching_scope': 'this fine-tuning stage only; pretrained candidate ancestry has other sources',
              'patient_independence_proven': False, 'historical_test_used': False, 'test_evaluated': training['test_evaluated']}
    (directory/'exact_input_lineage.json').write_text(json.dumps(result, indent=2))
    metadata_path = directory/'nail_color_classifier_labels.json'
    metadata = json.loads(metadata_path.read_text())
    metadata.update(experimental=True, deployment_approved=False, validated_roi_modes=[],
                    unvalidated_conditions=['pallor'], label_target='anemia proxy; visible pallor not independently adjudicated',
                    exact_input_lineage_sha256=hashlib.sha256((directory/'exact_input_lineage.json').read_bytes()).hexdigest())
    metadata_path.write_text(json.dumps(metadata,indent=2))
    print(json.dumps({'counts': result['counts'], 'historical_test_used':False}),flush=True)


if __name__ == '__main__':
    main()
