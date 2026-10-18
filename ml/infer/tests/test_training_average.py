import pytest

torch = pytest.importorskip('torch')
from ml.train.model_average import WarmupEMA


def test_first_trained_step_replaces_random_initialization():
    model = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(100)
    average = WarmupEMA(model)
    with torch.no_grad():
        model.weight.fill_(2)
    average.update(model)
    assert average.shadow['weight'].item() == 2
    assert average.initial_weight == 0
    with torch.no_grad():
        model.weight.fill_(6)
    average.update(model)
    assert average.shadow['weight'].item() == pytest.approx(5)
    assert model.weight.item() == 6


def test_float_buffers_follow_warmup_and_integer_buffers_are_copied():
    model = torch.nn.BatchNorm1d(2)
    average = WarmupEMA(model)
    for value in (2, 5):
        with torch.no_grad():
            model.running_mean.fill_(value)
            model.running_var.fill_(value + 1)
            model.num_batches_tracked.fill_(value)
        average.update(model)
    target = torch.nn.BatchNorm1d(2)
    average.copy_to(target)
    assert torch.all(target.running_mean == 4.25)
    assert torch.all(target.running_var == 5.25)
    assert target.num_batches_tracked.item() == 5
    assert average.shadow['running_mean'].data_ptr() != model.running_mean.data_ptr()


def test_short_run_tracks_training_and_respects_decay_ceiling():
    model = torch.nn.Linear(1, 1, bias=False)
    average = WarmupEMA(model, .5)
    for _ in range(105):
        with torch.no_grad():
            model.weight.fill_(1)
        average.update(model)
    assert average.shadow['weight'].item() == 1
    assert average.last_decay == .5
    assert average.updates == 105
    assert average.initial_weight == 0


@pytest.mark.parametrize('decay', [-.1, 1, float('nan'), float('inf')])
def test_invalid_decay_rejected(decay):
    with pytest.raises(ValueError, match='decay'):
        WarmupEMA(torch.nn.Linear(1, 1), decay)
