from . import (
    beaus_lines,
    appearance,
    classifier,
    clubbing,
    color_classifier,
    color_fusion,
    cyanosis,
    fusion,
    gradcam,
    image_quality,
    koilonychia,
    leukonychia,
    lindsays_nails,
    measurement_gate,
    melanonychia,
    muehrckes_lines,
    nail_region,
    nail_locator,
    onychogryphosis,
    onycholysis,
    pallor,
    pitting,
    skin_tone,
    specialists,
    splinter_hemorrhages,
    terrys_nails,
    validation_policy,
)
from .keypoints import find_keypoints
from .preprocessing import (
    BLUR_THRESHOLD,
    decode_base64_image,
    extract_best_contour,
    focus_score,
    is_flat_frame,
)

# Color/texture conditions measured from the top-down nail region, in display order
# (grouped: overall colour, then proximal/distal patterns, then surface markings).
_COLOR_CONDITIONS = (
    leukonychia,
    melanonychia,
    pallor,
    cyanosis,
    terrys_nails,
    lindsays_nails,
    onycholysis,
    beaus_lines,
    muehrckes_lines,
    splinter_hemorrhages,
    pitting,
    onychogryphosis,
)


def _inconclusive_findings(failure_reason):
    return [
        clubbing.inconclusive_finding(failure_reason),
        koilonychia.inconclusive_finding(failure_reason),
    ]


def _color_inconclusive(failure_reason):
    return [c.inconclusive_finding(failure_reason) for c in _COLOR_CONDITIONS]


def _extract(image_b64, require_keypoints=True):
    """Decode + locate a finger contour, optionally also its A/B/C keypoints.

    Returns (contour, keypoints, failure_reason). keypoints is None and
    failure_reason is set on any rejection; keypoints stays None (with no
    failure) when require_keypoints=False and only a contour is needed, e.g.
    validating the top-down photo, which isn't shaped like a side profile so
    the cuticle-vertex search doesn't apply to it.
    """
    image = decode_base64_image(image_b64)
    if image is None:
        return None, None, "invalid_image"

    if is_flat_frame(image):
        return None, None, "camera_feed_blank"

    if focus_score(image) < BLUR_THRESHOLD:
        return None, None, "too_blurry"

    contour, contour_validation = extract_best_contour(image)
    if not contour_validation["is_valid"]:
        return None, None, contour_validation["reason"]

    if not require_keypoints:
        return contour, None, None

    # primary_edge/frame_size (set only when the contour touched a border --
    # i.e. never for padded dataset crops) tell find_keypoints which side the
    # hand continues off-frame on, so it can pick the *opposite* extremum as
    # the tip instead of assuming the dataset's fixed top-to-bottom orientation.
    entry_edge = contour_validation.get("primary_edge")
    frame_size = contour_validation.get("frame_size")

    keypoints, kp_validation = find_keypoints(contour, entry_edge=entry_edge, frame_size=frame_size)
    if not kp_validation["is_valid"]:
        return contour, None, kp_validation["reason"]

    # Keypoints that move to a different verdict when the photo is re-saved/blurred/
    # rescaled are noise, not anatomy -- see measurement_gate.py.
    gate_failure, stability = measurement_gate.check(image, contour, keypoints)
    if gate_failure:
        return contour, None, gate_failure
    keypoints = {**keypoints, "confidence": round(keypoints["confidence"] * stability, 3)}

    return contour, keypoints, None


def validate_photo(image_b64, require_keypoints=True, top_nail_bbox=None):
    """Quick check used right after capture, before the full /analyze round trip."""
    if not require_keypoints and top_nail_bbox is not None:
        image = decode_base64_image(image_b64)
        if image is None:
            return False, 'invalid_image'
        if is_flat_frame(image):
            return False, 'camera_feed_blank'
        if focus_score(image) < BLUR_THRESHOLD:
            return False, 'too_blurry'
        reason = nail_locator.roi_quality(image, top_nail_bbox)
        return reason is None, reason
    _, _, failure_reason = _extract(image_b64, require_keypoints=require_keypoints)
    if (require_keypoints and failure_reason
            and color_classifier.model_metadata().get('validated_appearance_conditions')):
        # A readable finger can advance to top-photo appearance screening. It does
        # not make the failed side measurement valid.
        _, _, contour_failure = _extract(image_b64, require_keypoints=False)
        if contour_failure is None:
            return True, None
    return failure_reason is None, failure_reason


def propose_nail_bbox(image_b64):
    image = decode_base64_image(image_b64)
    if image is None or is_flat_frame(image) or focus_score(image) < BLUR_THRESHOLD:
        return None
    proposals = nail_locator.detect(image)
    if proposals:
        return proposals[0]['bbox']
    contour, validation = extract_best_contour(image)
    if validation['is_valid']:
        region, reason = nail_region.compute_nail_region(image, contour)
        if not reason:
            return list(region['bbox_norm'])
    return None


def analyze_side_profile(side_image_b64):
    """Geometry-only findings (clubbing angle + koilonychia sagitta) from the side photo."""
    contour, keypoints, failure_reason = _extract(side_image_b64, require_keypoints=True)
    if failure_reason:
        return {"findings": _inconclusive_findings(failure_reason)}

    confidence = keypoints["confidence"]
    findings = [
        clubbing.build_finding(
            keypoints["A"], keypoints["B"], keypoints["C"], keypoints["cuticle_is_concave"], confidence
        ),
        koilonychia.build_finding(contour, keypoints, confidence),
    ]
    return {"findings": findings}


def _ml_finding(image_b64, view):
    """One trained-CNN finding for a photo, or None if it can't be produced."""
    image = decode_base64_image(image_b64)
    if image is None:
        return None
    try:
        return classifier.build_finding(image, view)
    except Exception:  # noqa: BLE001 -- ML track must never break the geometry response
        return None


def _gradcam_b64(image_b64):
    """Base64 'what the AI looked at' heatmap for the top photo, or None."""
    image = decode_base64_image(image_b64)
    if image is None:
        return None
    return gradcam.overlay_b64(image)


def _photo_quality(image):
    """Focus-only quality dict for a decoded photo, or a zero score if it won't decode."""
    if image is None:
        return {"score": 0, "band": "poor", "issues": []}
    return image_quality.photo_quality(focus_score(image))


def analyze_top_color(top_image_b64, top_nail_bbox=None):
    """Color/texture findings (see _COLOR_CONDITIONS) from the top-down photo.

    Returns (findings, overlay, quality). overlay is {"top_bbox_norm":
    [x0,y0,x1,y1] in 0..1, "skin_ita": float|None} when the nail region was located
    (so the UI can show *what* was measured), else {"top_bbox_norm": None,
    "skin_ita": None}. quality is the top photo's photo_quality() dict -- focus-only
    on the early-failure paths, focus+glare+polish once the nail region is sampled.

    Classical CV like the geometry track -- no trained model needed, so this runs
    even in a torch-free environment. The top-down view is the right one for these:
    they're about the nail plate's color, not its side-profile shape. On any photo
    failure the color findings come back inconclusive with the same reason rather
    than measuring color on a region that wasn't reliably located.
    """
    from . import routing
    try:
        runtime = routing.configured_runtime()
    except (OSError, ValueError, TypeError, KeyError):
        return _color_inconclusive('routing_configuration_invalid'), {'top_bbox_norm': None, 'skin_ita': None}, _photo_quality(None)
    if runtime is not None:
        return runtime.top(top_image_b64, top_nail_bbox)
    no_overlay = {"top_bbox_norm": None, "skin_ita": None}
    image = decode_base64_image(top_image_b64)
    if image is None:
        return _color_inconclusive("invalid_image"), no_overlay, _photo_quality(None)
    quality = _photo_quality(image)
    if is_flat_frame(image):
        return _color_inconclusive("camera_feed_blank"), no_overlay, quality
    if focus_score(image) < BLUR_THRESHOLD:
        return _color_inconclusive("too_blurry"), no_overlay, quality
    bbox = top_nail_bbox
    roi_mode = 'assisted' if bbox is not None else 'legacy'
    if bbox is None:
        proposals = nail_locator.detect(image)
        if proposals:
            bbox, roi_mode = proposals[0]['bbox'], 'detector'
    if bbox is not None:
        reason = nail_locator.roi_quality(image, bbox)
        if reason:
            return _color_inconclusive(reason), no_overlay, quality
    contour, validation = extract_best_contour(image)
    region, reason = ((nail_region.compute_nail_region(image, contour, nail_bbox=bbox) if bbox is not None
                       else nail_region.compute_nail_region(image, contour)) if validation['is_valid']
                      else (None, validation['reason']))
    if reason and bbox is None:
        return _color_inconclusive(reason), no_overlay, quality
    if region is None:
        findings = _color_inconclusive(reason)
        region = {'bbox_norm': bbox, 'skin_ita': None}
    else:
        quality = image_quality.photo_quality(
            focus_score(image), image_quality.glare_fraction(region['V']),
            image_quality.polish_fraction(region['S']))
        findings = [c.build_finding(region) for c in _COLOR_CONDITIONS]
    cnn_region = {**region, 'bbox_norm': bbox} if bbox is not None else region
    # Region located: refine quality with glare/polish measured on the actual nail plate.
    pred = None

    # Optional trained-CNN second opinion: where it has a confident call on one of its
    # covered conditions it leads, else the classical heuristic stands (see color_fusion).
    # Gated by is_available() and wrapped so the CNN can never break the classical track.
    if color_classifier.is_available():
        try:
            pred = color_classifier.predict_from_region(image, cnn_region)
            if 'V' in region:
                findings = color_fusion.fuse(findings, pred, color_classifier.app_conditions())
            else:
                findings = color_fusion.fuse_roi(findings, pred, color_classifier.app_conditions())
        except Exception:  # noqa: BLE001 -- ML must never break the color response
            pass

    # Signs with a dedicated fine-tuned specialist (specialists.ENABLED: the heuristics are
    # near-chance on them); same never-break-the-response contract as the CNN above.
    if cnn_region.get('bbox_norm') is not None:
        try:
            findings = specialists.apply(findings, image, cnn_region['bbox_norm'])
        except Exception:  # noqa: BLE001
            pass

    # Honest skin-tone gating: the color findings are largely unvalidated on darker
    # tones (see ml/eval/audit_skin_tone.py), so cap confidence + attach a caveat
    # when this scan's skin tone is under-represented in our data.
    findings = skin_tone.apply_coverage(findings, region["skin_ita"])
    # Conditions that failed the end-to-end evidence bar don't get to assert a verdict.
    findings = validation_policy.apply(findings, roi_mode)

    overlay = {
        "top_bbox_norm": list(cnn_region["bbox_norm"]),
        'roi_mode': roi_mode,
        '_prediction': pred,
        "skin_ita": region["skin_ita"],
        "skin_tone": skin_tone.skin_tone_summary(region["skin_ita"]),
    }
    return findings, overlay, quality


def analyze(side_image_b64, top_image_b64, top_nail_bbox=None):
    """Full response: geometry (side photo) fused with the trained-CNN track, plus
    the color/texture track on the top-down photo.

    Geometry measures the side profile. The CNN classifies the top-down photo
    (its trained view), and fusion.fuse() combines the two into one finding per
    geometry condition: agreeing tracks boost confidence, disagreeing tracks return
    inconclusive rather than asserting a split verdict. The color track adds its own
    standalone findings (leukonychia, melanonychia, Terry's nails, Beau's lines,
    splinter hemorrhages, pitting) from the top-down photo.

    If torch or the weights aren't present (classifier.is_available() is False), the
    geometry findings stand on their own unchanged; the color track runs regardless
    -- the app still works, with full color findings, in a torch-free environment.
    """
    geometry = analyze_side_profile(side_image_b64)["findings"]
    color, overlay, top_quality = analyze_top_color(top_image_b64, top_nail_bbox)
    prediction = overlay.pop('_prediction', None)
    side_quality = _photo_quality(decode_base64_image(side_image_b64))
    image_quality_resp = {"side": side_quality, "top": top_quality}

    if classifier.is_available():
        ml_top = (_ml_finding(top_image_b64, 'top')
                  if any(f['verdict'] != 'inconclusive' for f in geometry) else None)
        geometry = fusion.fuse(geometry, ml_top)
        overlay['gradcam'] = _gradcam_b64(top_image_b64) if ml_top is not None else None
    routed_shapes = overlay.pop('_routed_shapes', None)
    if routed_shapes is not None:
        from .routing import merge_shape
        overlay['geometry_evidence'] = {finding['label']: finding for finding in geometry}
        geometry = [merge_shape(finding, routed_shapes[finding['label']]) for finding in geometry]
    else:
        geometry = appearance.fallback(geometry, prediction, overlay.get('roi_mode', 'legacy'))
    return {
        "findings": geometry + color,
        "overlay": overlay,
        "image_quality": image_quality_resp,
    }
