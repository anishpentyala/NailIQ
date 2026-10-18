"""Content-bound, experimental-only permission to show a reviewed combination."""
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_CHECKS = ('targets', 'protected_signs', 'healthy_scans', 'coverage',
                   'subgroups', 'reviewed', 'patient_independent', 'blinded',
                   'heldout', 'production_comparison', 'regression', 'device',
                   'phone', 'endpoint_parity')


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def identity(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def code_identity():
    paths = sorted((ROOT / 'ml/infer').glob('*.py')) + [ROOT / 'backend/app.py', ROOT / 'frontend/src/cameraGuide.js', ROOT / 'ml/nail_detection_model.py']
    paths += [ROOT / name for name in ('ml/eval/withholding_checks.py', 'ml/eval/confirmation_cohort.py',
                                      'scripts/evaluate_goal60_confirmation.py')]
    return identity({p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths if p.is_file()})


def dependency_identity(dependencies):
    return identity({Path(path).name: digest for path, digest in dependencies.items()})


def bundle_identity(runtime):
    active = {cfg['model'] for cfg in runtime.spec['conditions'].values()} | {'baseline'}
    return identity({'conditions': runtime.spec['conditions'],
        'models': {key: dependency_identity(model.dependencies) for key, model in runtime.models.items() if key in active},
        'locator': dependency_identity(runtime.locator.dependencies) if runtime.locator else None,
        'code': code_identity()})


def context(runtime, condition, config, branch, rules, bundle=None):
    kind = 'appearance' if condition in ('clubbing', 'koilonychia') else (
        'roi_only_color' if branch.get('roi_only') else 'measured_color')
    return {'condition': condition, 'roi_mode': branch['mode'], 'evidence_type': kind,
        'context_sha256': identity({'bundle': bundle or bundle_identity(runtime), 'condition': condition,
            'config': config, 'mode': branch['mode'], 'kind': kind, 'effective_rules': rules})}


def report_approves(report, grant, bundle):
    if not isinstance(report, dict) or not isinstance(report.get('checks'), dict):
        return False
    checks = report.get('checks', {})
    if (report.get('version') != 1 or report.get('phase') != 'fresh_confirmation'
            or report.get('bundle_sha256') != bundle
            or any(checks.get(key) is not True for key in REQUIRED_CHECKS)
            or not report.get('cohort_sha256') or report.get('healthy_patients', 0) < 400):
        return False
    eligible = report.get('eligible_contexts', [])
    if not isinstance(eligible, list):
        return False
    try:
        return any(isinstance(entry, dict) and entry.get('context') == grant and entry.get('positive_patients', 0) >= 150
                   and entry.get('healthy_patients', 0) >= 400 and .6 <= entry.get('recall', -1) <= 1
                   and 0 <= entry.get('healthy_fp_rate', -1) <= .05 for entry in eligible)
    except (TypeError, ValueError):
        return False


class EvidenceRegistry:
    def __init__(self, path, bundle):
        self.path = Path(path) if path else None
        self.dependencies, self.grants, self.errors = {}, set(), []
        if not self.path:
            return
        try:
            self.dependencies[str(self.path)] = file_hash(self.path)
            document = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(document, dict) or document.get('version') != 1 or not isinstance(document.get('records'), list):
                raise ValueError('Invalid validation evidence registry')
            for record in document['records']:
                try:
                    if not isinstance(record, dict):
                        raise ValueError('Invalid validation record')
                    grant = record['context']
                    if not isinstance(grant, dict):
                        raise ValueError('Invalid validation scope')
                    if set(grant) != {'condition', 'roi_mode', 'evidence_type', 'context_sha256'}:
                        raise ValueError('Invalid validation scope')
                    report_path = (self.path.parent / record['report_file']).resolve()
                    if not report_path.is_relative_to(self.path.parent.resolve()):
                        raise ValueError('Evidence report must stay inside its registry directory')
                    digest = file_hash(report_path)
                    self.dependencies[str(report_path)] = digest
                    if digest != record['report_sha256']:
                        raise ValueError('Evidence report hash mismatch')
                    report = json.loads(report_path.read_text(encoding='utf-8'))
                    if not report_approves(report, grant, bundle):
                        raise ValueError('Fresh confirmation requirements unmet')
                    self.grants.add(identity(grant))
                except (OSError, ValueError, KeyError, TypeError) as error:
                    self.errors.append(str(error))
        except (OSError, ValueError, TypeError) as error:
            self.errors.append(str(error))

    def allows(self, scope):
        # Revocation and report edits take effect even on an already cached runtime.
        try:
            unchanged = all(file_hash(path) == digest for path, digest in self.dependencies.items())
        except OSError:
            unchanged = False
        return unchanged and identity(scope) in self.grants
