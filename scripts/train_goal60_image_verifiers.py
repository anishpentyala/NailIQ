"""Train two calibrated EfficientNet replicas per target in isolated directories."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.infer.validation_evidence import file_hash

TRAINING_SOURCES = ('ml/train/train_color_classifier.py', 'ml/train/train_classifier.py',
                    'ml/train/model_average.py', 'scripts/train_goal60_image_verifiers.py')


def train(out):
    if (out / 'models.lock.json').exists():
        raise ValueError('Frozen ensemble cannot be retrained')
    lock = {'version': 1, 'experimental': True, 'deployment_approved': False,
            'clinical_release_eligible': False, 'seeds': [42, 1337], 'max_epochs': 20,
            'ema_mode': 'warmup', 'training_code': {p: file_hash(ROOT / p) for p in TRAINING_SOURCES},
            'conditions': {}}
    for condition in ('terrys_nails', 'pallor'):
        data = out / condition
        manifest = json.loads((data / 'manifest.json').read_text())
        members = []
        combined = out / (condition + '_ensemble')
        if combined.exists():
            raise ValueError('Preserve previous ensemble')
        for seed in lock['seeds']:
            directory = out / f'{condition}_seed{seed}'
            if directory.exists():
                raise ValueError('Preserve previous training run')
            log = out / f'{condition}_seed{seed}.log'
            arguments = ['--condition', condition, '--backbone', 'efficientnet_b0', '--epochs', '20',
                '--ema-mode', lock['ema_mode'],
                '--seed', str(seed), '--batch-size', '64', '--workers', '2', '--selection', 'macro_recall',
                '--data-dir', str(data.resolve()), '--output-dir', str(directory.resolve()), '--checkpoint-every-epoch']
            code = "import sys,torch;sys.path.append('backend/venv/Lib/site-packages');torch.set_num_threads(2);from ml.train.train_color_classifier import main;main()"
            print(f'Training {condition}, seed {seed}, maximum 20 epochs', flush=True)
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run([sys.executable, '-u', '-c', code] + arguments,
                                        cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f'Training failed; retained diagnostic log: {log}')
            record = json.loads((directory / 'training_efficientnet_b0.json').read_text())
            if record['seed'] != seed or record['test_evaluated'] or record['epochs_run'] > 20:
                raise ValueError('Training protocol mismatch')
            if record['ema_mode'] != lock['ema_mode'] or record['best_initialization_weight'] != 0:
                raise ValueError('Training average did not discard initialization')
            meta = json.loads((directory / 'nail_color_classifier_labels.json').read_text())
            member = {**meta['ensemble'][0], 'weights_file': f'efficientnet_b0_seed{seed}.pt', 'seed': seed}
            combined.mkdir(exist_ok=True)
            shutil.copyfile(directory / meta['ensemble'][0]['weights_file'], combined / member['weights_file'])
            member['sha256'] = file_hash(combined / member['weights_file'])
            members.append(member)
        meta.update(ensemble=members, experimental=True, deployment_approved=False,
            validated_roi_modes=[], unvalidated_conditions=[condition], label_target=manifest['label_basis'],
            dataset_manifest_sha256=file_hash(data / 'manifest.json'))
        (combined / 'nail_color_classifier_labels.json').write_text(json.dumps(meta, indent=2))
        lock['conditions'][condition] = {'directory': str(combined.resolve()),
            'manifest_sha256': file_hash(combined / 'nail_color_classifier_labels.json'),
            'members': members, 'data_manifest_sha256': file_hash(data / 'manifest.json')}
    if any(file_hash(ROOT / p) != digest for p, digest in lock['training_code'].items()):
        raise ValueError('Training code changed during the experiment')
    (out / 'models.lock.json').write_text(json.dumps(lock, indent=2), encoding='utf-8')
    print('Both two-seed ensembles saved and frozen', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    train(ap.parse_args().out)
