"""Positive-only research shadow decisions; never bypass displayed validation."""
import math
import json
from pathlib import Path
from types import MappingProxyType

from ml.infer import nail_locator
from ml.infer.preprocessing import decode_base64_image
from ml.infer.routing import RoutingRuntime, ModelRuntime, LocatorRuntime
from ml.eval.routed_replay import replay

STAGES = {
    'terrys_nails': {'model': 'ensemble', 'route': 'detector_fallback', 'rules': [.45, .15, None]},
    'pallor': {'model': 'pallor', 'route': 'legacy', 'rules': [.25, None, .05]},
}


def runtime_reference(reference, device):
    reference = Path(reference)
    original = json.loads(reference.read_text())
    if device is None or original.get('device', 'cpu') == device:
        return reference
    alternative = reference.with_name(reference.stem + '_cpu.json')
    if device != 'cpu' or not alternative.is_file():
        raise ValueError('A matched CPU reference manifest is required')
    candidate = json.loads(alternative.read_text())
    if candidate.get('device') != 'cpu' or {k: v for k, v in candidate.items() if k != 'device'} != {k: v for k, v in original.items() if k != 'device'}:
        raise ValueError('CPU reference changes more than the inference device')
    return alternative


class StageEvidence(RoutingRuntime):
    """Same production branch extraction, loading only the two first-stage candidates."""
    def __init__(self, reference, device=None):
        super().__init__(runtime_reference(reference, device))
        needed = {spec['model'] for spec in STAGES.values()}
        if needed - set(self.models):
            raise ValueError('Missing first-stage models')
        self.models = MappingProxyType({k: v for k, v in self.models.items() if k in needed})
        if device is not None and device != self.device:
            self.device = device
            self.models = MappingProxyType({k: ModelRuntime(v.directory, device) for k, v in self.models.items()})
            if self.locator is not None:
                self.locator = LocatorRuntime(self.locator.directory, device)

    def top(self, *args, **kwargs):
        raise ValueError('Evidence-only runtime cannot supply endpoint findings')


def verifier_score(encoded, branches, model, condition):
    if 'legacy' not in branches:
        return None, 'unsupported_verifier_roi_mode'
    branch = branches.get('legacy', {})
    if branch.get('failure') or not branch.get('bbox'):
        return None, branch.get('failure') or 'nail_region_unclear'
    image = decode_base64_image(encoded)
    if image is None:
        return None, 'invalid_image'
    reason = nail_locator.roi_quality(image, branch['bbox'])
    if reason:
        return None, reason
    try:
        probability = model.predict(image, branch['bbox']).get(condition)
        if probability is None or not math.isfinite(probability) or not 0 <= probability <= 1:
            return None, 'verifier_probability_invalid'
        return probability, None
    except (ImportError, OSError, RuntimeError, ValueError, TypeError):
        return None, 'verifier_unavailable'


def raw_stage(record, metadata, condition):
    return replay(record, condition, metadata, STAGES[condition])[0]


def threshold(calibration):
    negatives = [r for r in calibration if r['labels'] == ['healthy']]
    if not negatives:
        raise ValueError('Calibration requires explicit target-negative images')
    scores = [r['probability'] for r in negatives if r['stage1'] == 'outside' and r['probability'] is not None]
    # A threshold above one explicitly disables additions when a negative scores one.
    return max(.5, math.nextafter(max(scores), math.inf)) if scores else .5


def shadow(reference, stage1, probability, cutoff):
    if reference not in ('within', 'outside', 'inconclusive'):
        raise ValueError('Actual displayed reference verdict required')
    if not math.isfinite(cutoff) or cutoff < .5 or cutoff > math.nextafter(1., math.inf):
        raise ValueError('Invalid frozen verifier cutoff')
    valid = probability is not None and math.isfinite(probability) and 0 <= probability <= 1
    addition = stage1 == 'outside' and valid and probability >= cutoff
    return {'actual_shown': reference,
            'hypothetical_shown': 'outside' if addition else reference,
            'added_positive': addition and reference != 'outside',
            'clinical_release_eligible': False}
