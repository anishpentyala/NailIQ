import json

import torch
from torch import nn

from ml.train.train_color_classifier import CropDataset, initialize_candidate


def test_alternate_crop_root_preserves_train_valid_test_boundaries(tmp_path):
    for split in ("train", "valid", "test"):
        folder = tmp_path / split / "healthy"
        folder.mkdir(parents=True)
        (folder / f"{split}.png").write_bytes(b"not decoded during sample discovery")
    training = CropDataset(["healthy"], "train", True, data_root=tmp_path)
    validation = CropDataset(["healthy"], "valid", False, data_root=tmp_path)
    assert [p.name for p, _ in training.samples] == ["train.png"]
    assert [p.name for p, _ in validation.samples] == ["valid.png"]


def test_quarantined_crop_is_not_reintroduced_with_alternate_root(tmp_path):
    folder = tmp_path / "train" / "healthy"
    folder.mkdir(parents=True)
    for name in ("keep.png", "leaked.png"):
        (folder / name).write_bytes(b"sample")
    ds = CropDataset(["healthy"], "train", True, data_root=tmp_path,
                     exclusions={"excluded_crops": ["train/healthy/leaked.png"]})
    assert [p.name for p, _ in ds.samples] == ["keep.png"]


def test_initialization_aligns_labels_instead_of_class_indices(tmp_path):
    def model(size):
        network = nn.Module()
        network.features = nn.Linear(2, 2)
        network.classifier = nn.Sequential(nn.Identity(), nn.Identity(), nn.Identity(), nn.Linear(2, size))
        return network
    source, target = model(2), model(3)
    with torch.no_grad():
        source.classifier[3].weight.copy_(torch.tensor([[1., 2.], [3., 4.]]))
        source.classifier[3].bias.copy_(torch.tensor([10., 20.]))
    novel = target.classifier[3].weight[1].detach().clone()
    torch.save(source.state_dict(), tmp_path / 'candidate.pt')
    (tmp_path / 'nail_color_classifier_labels.json').write_text(json.dumps({
        'classes': ['healthy', 'pitting'], 'ensemble': [{
            'backbone': 'mobilenet_v3_large', 'weights_file': 'candidate.pt'}]}))
    initialize_candidate(target, ['pitting', 'melanonychia', 'healthy'], 'mobilenet_v3_large', tmp_path)
    assert torch.equal(target.classifier[3].weight[0], source.classifier[3].weight[1])
    assert torch.equal(target.classifier[3].weight[2], source.classifier[3].weight[0])
    assert torch.equal(target.classifier[3].weight[1], novel)
    assert target.classifier[3].bias.tolist()[::2] == [20., 10.]
    assert torch.equal(target.features.weight, source.features.weight)
