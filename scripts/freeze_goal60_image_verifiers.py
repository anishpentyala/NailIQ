"""Freeze finite TTA-calibrated ensembles, preserving the original training runs."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ml.train import train_color_classifier as trainer
from ml.infer.color_classifier import _build_backbone
from ml.infer.validation_evidence import file_hash


def freeze(out):
    source_lock = json.loads((out / 'models.lock.json').read_text())
    for path, digest in source_lock.get('training_code', {}).items():
        if file_hash(ROOT / path) != digest:
            raise ValueError('Training code changed before freezing calibration')
    destination = out / 'calibrated'
    if destination.exists():
        raise ValueError('Preserve frozen calibration')
    destination.mkdir()
    lock = {'version': 1, 'experimental': True, 'deployment_approved': False,
        'clinical_release_eligible': False, 'seeds': [42, 1337], 'max_epochs': 20,
        'calibration': 'bounded NLL on TRAIN-derived calibration, horizontal-flip softmax average', 'conditions': {}}
    lock['training_code'] = source_lock.get('training_code', {})
    lock['ema_mode'] = source_lock.get('ema_mode', 'legacy')
    lock['original_models_lock_sha256'] = file_hash(out / 'models.lock.json')
    corrections = []
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    for condition in ('terrys_nails', 'pallor'):
        directory = destination / condition
        directory.mkdir()
        members = []
        data = out / condition
        inventory = json.loads((data / 'manifest.json').read_text())
        for seed in lock['seeds']:
            source = out / f'{condition}_seed{seed}'
            meta = json.loads((source / 'nail_color_classifier_labels.json').read_text())
            training = json.loads((source / 'training_efficientnet_b0.json').read_text())
            if training['seed'] != seed or training['test_evaluated'] or training['epochs_run'] > 20:
                raise ValueError('Training protocol changed')
            model = _build_backbone('efficientnet_b0', len(meta['classes']))
            weights = source / meta['ensemble'][0]['weights_file']
            model.load_state_dict(torch.load(weights, map_location='cpu', weights_only=True))
            model = model.to(device).eval()
            dataset = trainer.CropDataset(meta['classes'], 'valid', False, data_root=data)
            logits, targets = [], []
            with torch.inference_mode():
                for images, labels in DataLoader(dataset, batch_size=64, num_workers=0):
                    images = images.to(device)
                    logits.append(torch.stack((model(images), model(torch.flip(images, [3]))), 1).cpu())
                    targets.append(labels)
            temperature = trainer.fit_color_temperature(torch.cat(logits), torch.cat(targets))
            filename = f'efficientnet_b0_seed{seed}.pt'
            shutil.copyfile(weights, directory / filename)
            members.append({'backbone': 'efficientnet_b0', 'weights_file': filename,
                'temperature': temperature, 'seed': seed, 'sha256': file_hash(weights)})
            corrections.append({'condition': condition, 'seed': seed,
                'original_temperature': meta['ensemble'][0]['temperature'] if str(meta['ensemble'][0]['temperature']) != 'nan' else 'NaN',
                'bounded_tta_temperature': temperature, 'boundary': temperature <= .051 or temperature >= 99.,
                'training_record_sha256': file_hash(source / 'training_efficientnet_b0.json'),
                'weights_changed': False})
        meta.update(ensemble=members, experimental=True, deployment_approved=False,
            validated_roi_modes=[], unvalidated_conditions=[condition], label_target=inventory['label_basis'],
            dataset_manifest_sha256=file_hash(data / 'manifest.json'))
        manifest = directory / 'nail_color_classifier_labels.json'
        manifest.write_text(json.dumps(meta, indent=2, allow_nan=False))
        lock['conditions'][condition] = {'directory': str(directory.resolve()),
            'manifest_sha256': file_hash(manifest), 'members': members,
            'data_manifest_sha256': file_hash(data / 'manifest.json')}
    # Original training ensemble lock is retained, even if its calibration failed.
    dump = json.dumps(lock, indent=2, allow_nan=False)
    (destination / 'models.lock.json').write_text(dump)
    (destination / 'calibration.json').write_text(json.dumps(corrections, indent=2, allow_nan=False))
    print(json.dumps(corrections), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    torch.set_num_threads(2)
    freeze(ap.parse_args().out)
