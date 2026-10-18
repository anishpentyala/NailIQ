"""Serialize candidate GPU jobs; evaluate frozen copies without replacing production."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / 'ml/venv/Scripts/python.exe'
CPU_PYTHON = REPO / 'backend/venv/Scripts/python.exe'
RAW = REPO / 'data/raw'
EVAL = REPO / 'ml/eval'
EXCLUSIONS = RAW / 'goal60_exclusions_v3.json'
BOOTSTRAP = "import torch,importlib,sys; from pathlib import Path; sys.path.append(str(Path('backend/venv/Lib/site-packages').resolve())); torch.set_num_threads(2); sys.argv=sys.argv[1:]; module=importlib.import_module(Path(sys.argv[0]).with_suffix('').as_posix().replace('/','.')); module.main()"
CPU_BOOTSTRAP = "import torch,runpy,sys; torch.set_num_threads(2); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')"


def command(script, arguments, gpu=False):
    return [str(PYTHON if gpu else CPU_PYTHON), '-u', '-c', BOOTSTRAP if gpu else CPU_BOOTSTRAP,
            script, *map(str, arguments)]


def start(name, script, arguments, gpu=False):
    log = (EVAL / f'{name}.log').open('w', encoding='utf-8')
    process = subprocess.Popen(command(script, arguments, gpu), cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps({'started': name, 'pid': process.pid}), flush=True)
    return process, log


def finish(job, name):
    process, log = job
    code = process.wait()
    log.close()
    if code:
        raise RuntimeError(f'{name} failed, exit {code}; inspect ml/eval/{name}.log')
    print(json.dumps({'completed': name}), flush=True)


def evaluate(name, model, locator=None, mode='auto'):
    arguments = ['--split', 'valid', '--include-authorized', '--include-shapes', '--model-dir', model,
                 '--exclusions', EXCLUSIONS, '--cache', EVAL / f'{name}.json', '--roi-mode', mode]
    if locator:
        arguments += ['--locator-dir', locator]
    return start(name, 'ml/eval/eval_end_to_end.py', arguments)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', type=Path, default=RAW / 'goal60_authorized_v3_models')
    args = parser.parse_args()
    cache = RAW / 'goal60_torch_cache'
    checkpoint_dir = cache / 'hub/checkpoints'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    for filename in ['mobilenet_v3_large-5c1a4163.pth', 'efficientnet_b0_rwightman-7f5810bc.pth']:
        source = Path.home() / '.cache/torch/hub/checkpoints' / filename
        if not (checkpoint_dir / filename).is_file():
            shutil.copy2(source, checkpoint_dir / filename)
    os.environ['TORCH_HOME'] = str(cache)
    deadline = time.monotonic() + 4 * 3600
    ready = args.first / 'training_mobilenet_v3_large.json'
    while not ready.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError('Initial training did not finish within four hours')
        time.sleep(10)
    first = RAW / 'goal60_authorized_mobilenet_frozen'
    if first.exists():
        raise RuntimeError('Frozen candidate exists; do not overwrite its results')
    shutil.copytree(args.first, first)
    first_eval = evaluate('goal60_authorized_mobilenet_valid', first)
    locator = RAW / 'goal60_nail_locator'
    training = start('goal60_locator_training', 'ml/train/train_nail_locator.py', [
        '--out', locator, '--epochs', '3', '--batch-size', '1', '--exclusions', EXCLUSIONS,
        '--exclusions', RAW / 'goal60_authorized_cls/exclusions.json'], True)
    finish(training, 'goal60_locator_training')
    finish(first_eval, 'goal60_authorized_mobilenet_valid')
    first_detector_eval = evaluate('goal60_authorized_mobilenet_detector_valid', first, locator)
    efficient = RAW / 'goal60_authorized_efficientnet'
    training = start('goal60_authorized_efficientnet_training', 'ml/train/train_color_classifier.py', [
        '--backbone', 'efficientnet_b0', '--epochs', '30', '--batch-size', '8', '--workers', '2', '--checkpoint-every-epoch', '--selection', 'macro_recall',
        '--data-dir', RAW / 'goal60_authorized_cls', '--output-dir', efficient,
        '--exclusions', EXCLUSIONS, '--extra-train-dir', RAW / 'goal60_runtime_crops_v3',
        '--initialize-from', RAW / 'goal60_efficientnet_v2'], True)
    finish(first_detector_eval, 'goal60_authorized_mobilenet_detector_valid')
    finish(evaluate('goal60_authorized_mobilenet_annotation_valid', first, locator, 'annotation'),
           'goal60_authorized_mobilenet_annotation_valid')
    finish(training, 'goal60_authorized_efficientnet_training')
    ensemble = RAW / 'goal60_authorized_ensemble'
    if ensemble.exists():
        raise RuntimeError('Ensemble candidate exists; do not overwrite')
    shutil.copytree(first, ensemble)
    manifest = json.loads((ensemble / 'nail_color_classifier_labels.json').read_text())
    second = json.loads((efficient / 'nail_color_classifier_labels.json').read_text())
    if manifest['classes'] != second['classes']:
        raise RuntimeError('Ensemble class ordering differs')
    for member in second['ensemble']:
        shutil.copy2(efficient / member['weights_file'], ensemble / member['weights_file'])
        manifest['ensemble'].append(member)
    (ensemble / 'nail_color_classifier_labels.json').write_text(json.dumps(manifest, indent=2))
    finish(evaluate('goal60_authorized_ensemble_legacy_valid', ensemble), 'goal60_authorized_ensemble_legacy_valid')
    finish(evaluate('goal60_authorized_ensemble_detector_valid', ensemble, locator),
           'goal60_authorized_ensemble_detector_valid')
    finish(evaluate('goal60_authorized_ensemble_annotation_valid', ensemble, locator, 'annotation'),
           'goal60_authorized_ensemble_annotation_valid')
    print('VALID candidate diagnostics complete. TEST and production weights remain untouched.', flush=True)


if __name__ == '__main__':
    main()
