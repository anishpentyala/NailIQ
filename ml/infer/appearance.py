"""Optional top-photo shape findings; a failed geometry measurement stays null."""
from . import color_classifier

SHAPES = {'clubbing', 'koilonychia'}


def signal(condition, probs, rules=None):
    rules = rules or {}
    threshold = color_classifier.CLASS_CONFIDENCE_THRESHOLD.get(condition, rules.get('floor', 0.5))
    if probs.get(condition, 0) >= threshold and probs.get(condition, 0) >= probs.get('healthy', 0):
        return 'outside', probs[condition]
    if probs.get('healthy', 0) >= rules.get('healthy_floor', 0.5):
        return 'within', probs['healthy']
    return 'inconclusive', 0


def fallback(findings, prediction, roi_mode):
    metadata = color_classifier.model_metadata()
    covered = set(metadata.get('appearance_conditions', [])) & SHAPES
    probs = (prediction or {}).get('probs') or {}
    out = []
    for original in findings:
        geometry = original.get('geometry', original)
        condition = original['label']
        if condition not in covered or geometry['verdict'] != 'inconclusive' or not probs:
            out.append(original)
            continue
        rules = metadata.get('appearance_rules', {}).get(condition, {})
        verdict, confidence = signal(condition, probs, rules)
        if verdict == 'inconclusive':
            out.append(original)
            continue
        approved = (condition in metadata.get('validated_appearance_conditions', [])
                    and roi_mode in metadata.get('validated_roi_modes', []))
        out.append({**original, 'value': None, 'unit': None, 'track_used': 'appearance',
            'evidence_type': 'appearance', 'geometry': {**geometry, 'value': None},
            'ml': prediction, 'roi_mode': roi_mode,
            'verdict': verdict if approved else 'inconclusive',
            'confidence': confidence if approved else 0,
            'failure_reason': None if approved else 'not_validated',
            **({} if approved else {'unvalidated_verdict': verdict})})
    return out
