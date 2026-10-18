"""Compare tight versus actual CNN-crop focus on VALID retakes and synthetic blur."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from ml.eval.eval_color_sensitivity import b64
from ml.infer import color_classifier, nail_locator
from ml.infer.preprocessing import decode_base64_image, focus_score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--locator-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    metadata = json.loads(args.cache.with_suffix('.meta.json').read_text())
    if metadata['split'] != 'valid':
        raise SystemExit('Focus development must use VALID only')
    nail_locator._MODELS = args.locator_dir.resolve()
    selected, counts = [], {}
    for row in json.loads(args.cache.read_text()):
        if row['probs'] or next(iter(row['findings'].values()), {}).get('failure_reason') != 'too_blurry':
            continue
        source = Path(row['path']).parts[2]
        if counts.get(source, 0) >= 10:
            continue
        counts[source] = counts.get(source, 0) + 1
        image = decode_base64_image(b64(REPO / row['path']))
        proposals = nail_locator.detect(image)
        if not proposals:
            continue
        box = proposals[0]['bbox']
        x0, y0, x1, y1 = nail_locator.pixel_box(image, box)
        crop = color_classifier._crop_to_bbox(image, box)
        blurred = cv2.GaussianBlur(image, (0, 0), 3)
        selected.append({'path': row['path'], 'bbox': box,
                         'tight_focus': focus_score(image[y0:y1, x0:x1]),
                         'cnn_crop_focus': focus_score(crop),
                         'blurred_cnn_crop_focus': focus_score(color_classifier._crop_to_bbox(blurred, box))})
    args.out.write_text(json.dumps({'selection': 'first ten rejected VALID photos per source; no disease-score selection',
                                  'rows': selected}, indent=2))
    print(json.dumps({'sample_n': len(selected), 'padded_above_original_floor': sum(r['cnn_crop_focus'] >= 20 for r in selected),
                      'synthetic_blur_above_floor': sum(r['blurred_cnn_crop_focus'] >= 20 for r in selected),
                      'median_tight': float(np.median([r['tight_focus'] for r in selected])),
                      'median_cnn_crop': float(np.median([r['cnn_crop_focus'] for r in selected]))}), flush=True)


if __name__ == '__main__':
    main()
