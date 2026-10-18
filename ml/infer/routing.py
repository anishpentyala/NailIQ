"""Opt-in candidate routing; immutable rules and explicit per-branch evidence."""
import hashlib
import json
import math
import os
import threading
from pathlib import Path
from types import MappingProxyType

import cv2

from . import color_classifier, color_fusion, image_quality, nail_locator, nail_region, skin_tone, validation_policy, validation_evidence
from .preprocessing import BLUR_THRESHOLD, decode_base64_image, extract_best_contour, focus_score, is_flat_frame

ROUTES = ('legacy', 'detector', 'detector_fallback')
SHAPES = ('clubbing', 'koilonychia')
_lock = threading.RLock()
_configured = {}
_models = {}


def immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({key: immutable(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(immutable(item) for item in value)
    return value


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def rules_for(metadata, condition, override=None):
    tables = {'floors': dict(color_classifier._DEFAULT_CLASS_THRESHOLDS),
              'ovr': dict(color_fusion._DEFAULT_OVR), 'support': dict(color_fusion._DEFAULT_SUPPORT)}
    entries = dict(metadata.get('decision_rules', {}))
    if override is not None:
        entries[condition] = override
    for label, values in entries.items():
        if not isinstance(values, (list, tuple)) or len(values) != 3:
            raise ValueError('Invalid decision rule')
        for table, value in zip(tables.values(), values):
            if value is None:
                table.pop(label, None)
            elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Invalid decision threshold')
            else:
                table[label] = value
    appearance = dict(metadata.get('appearance_rules', {}).get(condition, {}))
    if condition in SHAPES and override is not None:
        appearance['floor'] = override[0] if override[0] is not None else 0.5
    return {**{key: MappingProxyType(value) for key, value in tables.items()},
            'appearance': MappingProxyType(appearance)}


def decide(condition, branch, metadata, override=None):
    heur = dict(branch['heuristics'][condition])
    if branch.get('failure'):
        return {**heur, 'verdict': 'inconclusive', 'confidence': 0, 'failure_reason': branch['failure']}
    rules = rules_for(metadata, condition, override)
    probs = branch.get('probs')
    if not probs:
        # A routed model failure must not silently substitute a different model.
        return {**heur, 'verdict': 'inconclusive', 'confidence': 0,
                'failure_reason': branch.get('model_failure') or 'routed_model_unavailable'}
    prediction = color_classifier.opinion_from_probs(probs, rules['floors'])
    if condition in SHAPES:
        thresholds = rules['appearance']
        floor = thresholds.get('floor', rules['floors'].get(condition, 0.5))
        if probs.get(condition, 0) >= floor and probs.get(condition, 0) >= probs.get('healthy', 0):
            verdict, confidence = 'outside', probs[condition]
        elif probs.get('healthy', 0) >= thresholds.get('healthy_floor', 0.5):
            verdict, confidence = 'within', probs['healthy']
        else:
            verdict, confidence = 'inconclusive', 0
        return {**heur, 'verdict': verdict, 'confidence': confidence, 'value': None, 'unit': None,
                'track_used': 'appearance', 'evidence_type': 'appearance', 'ml': prediction,
                'failure_reason': None if verdict != 'inconclusive' else 'low_confidence'}
    if condition not in metadata.get('app_conditions', []):
        return heur
    if branch.get('roi_only'):
        return color_fusion.fuse_roi([heur], prediction, [condition], rules)[0]
    return color_fusion._fuse_one(heur, prediction, rules)


def choose(condition, branches, metadata, route, override=None):
    if 'assisted' in branches:
        key = 'assisted'
    elif route == 'legacy':
        key = 'legacy'
    else:
        key = 'detector'
    result = decide(condition, branches[key], metadata, override)
    if key != 'assisted' and route == 'detector_fallback' and result['verdict'] == 'inconclusive':
        key = 'legacy'
        result = decide(condition, branches[key], metadata, override)
    return result, key


class ModelRuntime:
    def __init__(self, directory, device='cpu'):
        self.device = device
        self.directory = Path(directory).resolve()
        self.manifest_path = self.directory / 'nail_color_classifier_labels.json'
        self.metadata = json.loads(self.manifest_path.read_text())
        meta = self.metadata
        classes = meta.get('classes', [])
        if not classes or len(set(classes)) != len(classes) or 'healthy' not in classes:
            raise ValueError('Invalid routed class mapping')
        if not isinstance(meta.get('img_size'), int) or not 8 <= meta['img_size'] <= 512:
            raise ValueError('Invalid image size')
        for name in ('mean', 'std'):
            values = meta.get(name)
            if not isinstance(values, list) or len(values) != 3 or any(
                    not isinstance(v, (int, float)) or not math.isfinite(v) or (name == 'std' and v <= 0) for v in values):
                raise ValueError('Invalid normalization')
        self.members = color_classifier._members_from_meta(meta)
        if not self.members:
            raise ValueError('Missing routed members')
        self.dependencies = {str(self.manifest_path): digest(self.manifest_path)}
        for backbone, filename, temperature in self.members:
            path = (self.directory / filename).resolve()
            if path.parent != self.directory or not math.isfinite(temperature) or temperature <= 0:
                raise ValueError('Invalid routed weights or temperature')
            self.dependencies[str(path)] = digest(path)
        self.identity = (device, tuple(sorted(self.dependencies.items())))
        self.metadata = immutable(self.metadata)
        self._loaded = None
        self._load_lock = threading.RLock()

    def predict(self, image, bbox):
        import torch
        from torchvision import transforms
        with self._load_lock:
            if self._loaded is None:
                with _lock:
                    loaded = _models.get(self.identity)
                    if loaded is None:
                        if any(digest(path) != expected for path, expected in self.dependencies.items()):
                            raise ValueError('Routed model changed before loading')
                        members = []
                        for backbone, filename, temperature in self.members:
                            model = color_classifier._build_backbone(backbone, len(self.metadata['classes']))
                            model.load_state_dict(torch.load(self.directory / filename, map_location='cpu', weights_only=True))
                            members.append((model.to(self.device).eval(), temperature))
                        transform = transforms.Compose([
                            transforms.Resize(256, antialias=True), transforms.CenterCrop(self.metadata['img_size']),
                            transforms.Normalize(self.metadata['mean'], self.metadata['std'])])
                        loaded = (members, transform)
                        _models[self.identity] = loaded
                    self._loaded = loaded
        crop = color_classifier._crop_to_bbox(image, bbox)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255
        members, transform = self._loaded
        base = transform(tensor)
        views = torch.stack([base, torch.flip(base, dims=[2])]).to(self.device)
        with torch.inference_mode():
            probs = sum(torch.softmax(model(views) / temperature, dim=1).mean(dim=0)
                        for model, temperature in members) / len(members)
        return {label: round(float(probs[i]), 3) for i, label in enumerate(self.metadata['classes'])}


class LocatorRuntime:
    def __init__(self, directory, device='cpu'):
        self.device = device
        self.directory = Path(directory).resolve()
        path = self.directory / 'nail_locator.json'
        self.metadata = json.loads(path.read_text())
        self.weights = (self.directory / self.metadata.get('weights_file', 'nail_locator.pt')).resolve()
        if self.weights.parent != self.directory:
            raise ValueError('Invalid locator weights')
        self.dependencies = {str(path): digest(path), str(self.weights): digest(self.weights)}
        self.model = None
        self.lock = threading.RLock()

    def detect(self, image):
        import torch
        from ml.nail_detection_model import build_nail_detector
        with self.lock:
            if self.model is None:
                if any(digest(path) != expected for path, expected in self.dependencies.items()):
                    raise ValueError('Locator changed before loading')
                model = build_nail_detector()
                model.load_state_dict(torch.load(self.weights, map_location='cpu', weights_only=True))
                self.model = model.to(self.device).eval()
            tensor = (torch.from_numpy(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 255).to(self.device)
            with torch.inference_mode():
                result = self.model([tensor])[0]
        h, w = image.shape[:2]
        proposals = []
        for box, score in zip(result['boxes'].tolist(), result['scores'].tolist()):
            normalized = [max(0, min(1, v / size)) for v, size in zip(box, (w, h, w, h))]
            if score >= self.metadata.get('threshold', 0.5) and nail_locator.valid_bbox(normalized):
                proposals.append((score, normalized))
        return max(proposals)[1] if proposals else None


class RoutingRuntime:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.spec = json.loads(self.path.read_text())
        if self.spec.get('version') != 1 or self.spec.get('experimental') is not True:
            raise ValueError('Only versioned experimental routing is supported')
        self.device = self.spec.get('device', 'cpu')
        if self.device not in ('cpu', 'cuda:0'):
            raise ValueError('Invalid experimental inference device')
        if self.device != 'cpu':
            import torch
            if not torch.cuda.is_available():
                raise ValueError('Requested CUDA device is unavailable')
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
        from .pipeline import _COLOR_CONDITIONS
        self.modules = {m.__name__.rsplit('.', 1)[-1]: m for m in _COLOR_CONDITIONS}
        self.conditions = list(SHAPES) + list(self.modules)
        if set(self.spec.get('conditions', {})) != set(self.conditions):
            raise ValueError('Routing manifest must cover all 14 signs')
        self.models, self.model_errors = {}, {}
        self.dependencies = {str(self.path): digest(self.path)}
        for model_id, directory in self.spec['models'].items():
            try:
                model = ModelRuntime(self.path.parent / directory, self.device)
                self.models[model_id] = model
                self.dependencies.update(model.dependencies)
            except (OSError, ValueError, TypeError, KeyError) as error:
                self.model_errors[model_id] = str(error)
        for condition, config in self.spec['conditions'].items():
            if config.get('model') not in self.spec['models'] or config.get('route') not in ROUTES:
                raise ValueError('Invalid condition route')
            model = self.models.get(config['model'])
            if model is not None:
                if condition not in model.metadata['classes']:
                    self.model_errors[config['model']] = 'Model class mismatch'
                rules_for(model.metadata, condition, config.get('rules'))
        self.locator = None
        self.locator_error = None
        if self.spec.get('locator'):
            try:
                self.locator = LocatorRuntime(self.path.parent / self.spec['locator'], self.device)
                self.dependencies.update(self.locator.dependencies)
            except (OSError, ValueError, TypeError, KeyError) as error:
                self.locator_error = str(error)
        self.bundle_sha256 = validation_evidence.bundle_identity(self)
        registry = self.spec.get('validation_evidence')
        self.validation = validation_evidence.EvidenceRegistry(self.path.parent / registry if registry else None, self.bundle_sha256)
        self.dependencies.update(self.validation.dependencies)
        self.spec = immutable(self.spec)
        self.models = MappingProxyType(self.models)
        self.model_errors = MappingProxyType(self.model_errors)

    def heuristics(self, reason):
        result = {condition: module.inconclusive_finding(reason) for condition, module in self.modules.items()}
        for condition in SHAPES:
            result[condition] = {'label': condition, 'display_name': condition, 'value': None, 'unit': None,
                                 'verdict': 'inconclusive', 'confidence': 0, 'failure_reason': reason,
                                 'track_used': 'appearance'}
        return result

    def branch(self, image, contour, contour_reason, bbox, mode, failure=None):
        if failure is None and bbox is not None:
            failure = nail_locator.roi_quality(image, bbox)
        region = None
        if failure is None:
            if contour_reason is None:
                region, reason = nail_region.compute_nail_region(image, contour, nail_bbox=bbox)
            else:
                reason = contour_reason
            if region is None and bbox is None:
                failure = reason
        heuristics = self.heuristics(failure or 'nail_region_unclear')
        if region is not None:
            heuristics.update({condition: module.build_finding(region) for condition, module in self.modules.items()})
            bbox = list(region['bbox_norm']) if bbox is None else bbox
        models = {}
        for model_id, model in self.models.items():
            probs, error = None, None
            if failure is None and model_id not in self.model_errors:
                try:
                    probs = model.predict(image, bbox)
                except (ImportError, OSError, RuntimeError, ValueError, TypeError):
                    error = 'routed_model_unavailable'
            models[model_id] = {'probs': probs, 'failure': error or self.model_errors.get(model_id)}
        quality = image_quality.photo_quality(focus_score(image),
                  image_quality.glare_fraction(region['V']), image_quality.polish_fraction(region['S'])) if region is not None else None
        return {'mode': mode, 'bbox': bbox, 'failure': failure, 'heuristics': heuristics, 'quality': quality,
                'roi_only': region is None, 'skin_ita': region.get('skin_ita') if region else None, 'models': models}

    def evidence(self, encoded, assisted=None):
        image = decode_base64_image(encoded)
        reason = ('invalid_image' if image is None else 'camera_feed_blank' if is_flat_frame(image)
                  else 'too_blurry' if focus_score(image) < BLUR_THRESHOLD else None)
        quality = {'score': 0, 'band': 'poor', 'issues': []} if image is None else image_quality.photo_quality(focus_score(image))
        if reason:
            branches = {
                key: {'mode': key, 'bbox': None, 'failure': reason, 'heuristics': self.heuristics(reason),
                      'roi_only': False, 'skin_ita': None, 'models': {}}
                for key in (('assisted',) if assisted is not None else ('legacy', 'detector'))}
            return branches, quality
        contour, validation = extract_best_contour(image)
        contour_reason = None if validation['is_valid'] else validation['reason']
        if assisted is not None:
            return {'assisted': self.branch(image, contour, contour_reason, assisted, 'assisted')}, quality
        legacy = self.branch(image, contour, contour_reason, None, 'legacy')
        try:
            bbox = self.locator.detect(image) if self.locator is not None else None
        except (ImportError, OSError, RuntimeError, ValueError, TypeError):
            bbox = None
        if bbox is None:
            reason = 'nail_locator_unavailable' if self.locator is None else 'nail_not_detected'
            detector = self.branch(image, contour, contour_reason, None, 'detector', failure=reason)
        else:
            detector = self.branch(image, contour, contour_reason, bbox, 'detector')
        return {'legacy': legacy, 'detector': detector}, quality

    def selected(self, evidence, condition, config=None):
        config = config or self.spec['conditions'][condition]
        model_id = config['model']
        model = self.models.get(model_id)
        metadata = model.metadata if model else {}
        branches = {key: {**value, 'probs': value['models'].get(model_id, {}).get('probs'),
                          'model_failure': value['models'].get(model_id, {}).get('failure') or 'routed_model_unavailable'}
                    for key, value in evidence.items()}
        raw, key = choose(condition, branches, metadata, config['route'], config.get('rules'))
        branch = evidence[key]
        result = {**raw, 'model_id': model_id, 'route_id': key, 'roi_mode': branch['mode'], 'bbox_norm': branch['bbox']}
        result = skin_tone.apply_coverage([result], branch['skin_ita'])[0]
        scope = validation_evidence.context(self, condition, config, branch,
                                           rules_for(metadata, condition, config.get('rules')), self.bundle_sha256)
        evidence_approved = self.validation.allows(scope)
        if condition in SHAPES:
            approved = evidence_approved or (condition in metadata.get('validated_appearance_conditions', []) and branch['mode'] in metadata.get('validated_roi_modes', []))
            if result['verdict'] != 'inconclusive' and not approved:
                result = {**result, 'unvalidated_verdict': result['verdict'], 'verdict': 'inconclusive',
                          'confidence': 0, 'failure_reason': 'not_validated'}
        else:
            result = validation_policy.apply([result], branch['mode'], metadata, approved=evidence_approved)[0]
        return result

    def top(self, encoded, assisted=None):
        evidence, quality = self.evidence(encoded, assisted)
        selected = {c: self.selected(evidence, c) for c in self.conditions}
        boxes = {json.dumps(f['bbox_norm']) for f in selected.values()}
        modes = {f['roi_mode'] for f in selected.values()}
        first = next(iter(evidence.values()))
        quality = first.get('quality') or quality
        overlay = {'top_bbox_norm': next(iter(selected.values()))['bbox_norm'] if len(boxes) == 1 else None,
                   'roi_mode': next(iter(modes)) if len(modes) == 1 else 'mixed',
                   'condition_rois': {c: {'bbox_norm': f['bbox_norm'], 'roi_mode': f['roi_mode']} for c, f in selected.items()},
                   'skin_ita': first['skin_ita'], 'skin_tone': skin_tone.skin_tone_summary(first['skin_ita']),
                   'routing_digest': self.dependencies[str(self.path)], 'routing_evidence': evidence,
                   '_routed_shapes': {c: selected[c] for c in SHAPES}}
        return [selected[c] for c in self.modules], overlay, quality


def merge_shape(original, candidate):
    geometry = original.get('geometry', original)
    if geometry['verdict'] != 'inconclusive' or candidate.get('verdict') == 'inconclusive' and 'unvalidated_verdict' not in candidate:
        return original
    return {**original, **candidate, 'geometry': {**geometry, 'value': None}, 'value': None, 'unit': None}


def configured_runtime():
    value = os.environ.get('NAILIQ_ROUTING_MANIFEST')
    if not value:
        return None
    path = Path(value).resolve()
    identity = (str(path), digest(path))
    with _lock:
        if identity not in _configured:
            _configured[identity] = RoutingRuntime(path)
        return _configured[identity]
