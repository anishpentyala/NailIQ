"""Nail orientation: which way the fingertip (free edge) points, and rotation to tip-down.

Direction letters are as seen in the image: D down, R right, U up, L left. A crop
photographed with the tip on the right is rotated 90 degrees clockwise to put the tip
at the bottom. The color CNN is shown tip-down crops only when its manifest says
"canonical_orientation": true.

Two sources of direction: the finger's own geometry at run time (`direction_from_vector`
-- the app already knows the finger axis), and a small learned tagger for dataset crops
that have no finger silhouette (`TipDirectionTagger`, trained by
scripts/tag_nail_orientation.py).
"""

from pathlib import Path

import cv2
import numpy as np

WEIGHTS = Path(__file__).resolve().parent.parent / "models" / "nail_orientation_resnet18.pt"
_ORDER = "DRUL"  # class k == a tip-down crop turned k quarter-turns counter-clockwise
TAG_SIZE = 160


def direction_from_vector(vx, vy):
    """Snap an image-space vector (x right, y down) pointing at the fingertip to D/R/U/L."""
    if abs(vx) > abs(vy):
        return "R" if vx > 0 else "L"
    return "D" if vy > 0 else "U"


def rotate_tip_down(image, direction):
    """Rotate by whole quarter-turns so the tip points down. Lossless; direction in DRUL."""
    return np.ascontiguousarray(np.rot90(image, -_ORDER.index(direction)))


class TipDirectionTagger:
    """ResNet18 rotation classifier; lazy torch import so the app stays torch-optional."""

    def __init__(self, weights=WEIGHTS):
        import torch
        import torch.nn as nn
        from torchvision import models
        self.torch = torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        m = models.resnet18(weights=None)
        m.fc = nn.Linear(512, 4)
        m.load_state_dict(torch.load(weights, map_location="cpu"))
        self.model = m.to(self.dev).eval()
        self.mean = torch.tensor([0.485, 0.456, 0.406])[:, None, None]
        self.std = torch.tensor([0.229, 0.224, 0.225])[:, None, None]

    def _tensor(self, rgb):
        x = self.torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float() / 255
        return (x - self.mean) / self.std

    def tag(self, bgr):
        """Return (direction, confidence) averaged over the four rotations of the crop."""
        rgb = cv2.cvtColor(cv2.resize(bgr, (TAG_SIZE, TAG_SIZE)), cv2.COLOR_BGR2RGB)
        batch = self.torch.stack([self._tensor(np.rot90(rgb, k)) for k in range(4)]).to(self.dev)
        with self.torch.no_grad():
            p = self.torch.softmax(self.model(batch), 1).cpu().numpy()
        # a crop turned k extra quarter-turns reports (true + k): undo the k
        p = np.mean([np.roll(p[k], -k) for k in range(4)], axis=0)
        return _ORDER[int(p.argmax())], float(p.max())
