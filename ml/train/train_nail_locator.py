"""Train an isolated generic nail locator on trusted boxes and polygons; no TEST reads."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

import cv2
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision.ops import box_iou

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from ml.nail_detection_model import build_nail_detector
from scripts.build_color_classification_dataset import (
    CHAA, KNM, SPLITS, _row_bbox, bucket_split, find_image_file,
)
from scripts.prepare_color_exclusions import excludes_source


class NailBoxes(Dataset):
    def __init__(self, split, exclusions=(), limit=None):
        self.split = split
        self.rows = []
        for root, resplit in ((KNM, False), (CHAA, True)):
            for source_split in (SPLITS if resplit else (split,)):
                for annotation in sorted((root / source_split / 'labels').glob('*.txt')):
                    if resplit and bucket_split(annotation.stem) != split:
                        continue
                    path = find_image_file(annotation)
                    if path is None or any(excludes_source(path, item) for item in exclusions):
                        continue
                    boxes = []
                    for line in annotation.read_text().splitlines():
                        parts = line.split()
                        if len(parts) < 5:
                            continue
                        box = _row_bbox(list(map(float, parts[1:])))
                        if box is not None:
                            boxes.append(box)
                    if boxes:
                        self.rows.append((path, boxes))
        if limit is not None:
            random.Random(42).shuffle(self.rows)
            self.rows = self.rows[:limit]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        path, normalized = self.rows[index]
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f'Unreadable annotated image: {path}')
        h, w = image.shape[:2]
        boxes = []
        for cx, cy, bw, bh in normalized:
            x0, y0 = max(0, (cx - bw / 2) * w), max(0, (cy - bh / 2) * h)
            x1, y1 = min(w, (cx + bw / 2) * w), min(h, (cy + bh / 2) * h)
            if x1 > x0 and y1 > y0:
                boxes.append([x0, y0, x1, y1])
        if not boxes:
            raise RuntimeError(f'No valid nail boxes: {path}')
        tensor = torch.from_numpy(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 255
        boxes = torch.tensor(boxes, dtype=torch.float32)
        if self.split == 'train' and random.random() < 0.5:
            tensor = tensor.flip(-1)
            boxes[:, [0, 2]] = w - boxes[:, [2, 0]]
        return tensor, {'boxes': boxes, 'labels': torch.ones(len(boxes), dtype=torch.int64)}


def collate(batch):
    return tuple(zip(*batch))


@torch.inference_mode()
def evaluate(model, loader, device):
    model.eval()
    matched, total, emitted = 0, 0, 0
    for images, targets in loader:
        predictions = model([image.to(device) for image in images])
        for prediction, target in zip(predictions, targets):
            truth = target['boxes'].to(device)
            boxes = prediction['boxes'][prediction['scores'] >= 0.5]
            total += len(truth)
            emitted += len(boxes)
            if len(boxes):
                overlaps = box_iou(boxes, truth)
                # Each predicted and annotated box can match once.
                while overlaps.numel() and float(overlaps.max()) >= 0.5:
                    flat = int(overlaps.argmax())
                    row, col = divmod(flat, overlaps.shape[1])
                    matched += 1
                    overlaps[row, :] = -1
                    overlaps[:, col] = -1
    return {'recall_iou50': matched / total if total else 0,
            'precision_iou50': matched / emitted if emitted else 0,
            'matched': matched, 'annotated': total, 'predicted': emitted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--exclusions', type=Path, action='append', required=True)
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=1)
    parser.add_argument('--train-limit', type=int)
    parser.add_argument('--valid-limit', type=int)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit('Choose an empty candidate directory')
    args.out.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(2)
    exclusions = [json.loads(path.read_text()) for path in args.exclusions]
    train = NailBoxes('train', exclusions, args.train_limit)
    valid = NailBoxes('valid', exclusions, args.valid_limit)
    if not train or not valid:
        raise SystemExit('Both TRAIN and VALID need annotated images')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = build_nail_detector(pretrained=True).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    loader = DataLoader(train, batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    validation = DataLoader(valid, batch_size=1, collate_fn=collate)
    best = -1
    history = []
    print(json.dumps({'device': str(device), 'train': len(train), 'valid': len(valid)}), flush=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        loss_sum = 0
        for step, (images, targets) in enumerate(loader, 1):
            images = [image.to(device) for image in images]
            targets = [{key: value.to(device) for key, value in target.items()} for target in targets]
            losses = model(images, targets)
            loss = sum(losses.values())
            if not torch.isfinite(loss):
                raise RuntimeError('Nonfinite localization loss')
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach())
            if step % 200 == 0:
                print(f'epoch {epoch} step {step}/{len(loader)} loss {loss_sum / step:.4f}', flush=True)
        metrics = evaluate(model, validation, device)
        history.append({'epoch': epoch, 'loss': loss_sum / len(loader), **metrics})
        if metrics['recall_iou50'] > best:
            best = metrics['recall_iou50']
            torch.save({key: value.cpu() for key, value in model.state_dict().items()}, args.out / 'nail_locator.pt')
        metadata = {'architecture': 'fasterrcnn_mobilenet_v3_large_320_fpn',
            'weights_file': 'nail_locator.pt', 'threshold': 0.5, 'history': history,
            'train_images': len(train), 'valid_images': len(valid), 'test_evaluated': False,
            'experimental': True, 'partial_training': args.train_limit is not None or args.valid_limit is not None,
            'exclusion_hashes': [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.exclusions]}
        (args.out / 'nail_locator.json').write_text(json.dumps(metadata, indent=2))
        print(json.dumps(history[-1]), flush=True)


if __name__ == '__main__':
    main()
