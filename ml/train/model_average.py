"""Model averaging that does not retain a randomly initialized classifier head."""
import math

from ml.train.train_classifier import EMA


class WarmupEMA(EMA):
    def __init__(self, model, decay=0.999):
        if not math.isfinite(decay) or not 0 <= decay < 1:
            raise ValueError('EMA decay must be finite and in [0, 1)')
        super().__init__(model, decay)
        self.updates = 0
        self.last_decay = 0.0
        self.initial_weight = 1.0

    def update(self, model):
        self.updates += 1
        # Bootstrap from the first trained state. Then lengthen the averaging
        # window gradually; small datasets cannot wait thousands of steps.
        self.last_decay = (0.0 if self.updates == 1 else
                           min(self.decay, (1 + self.updates) / (10 + self.updates)))
        self.initial_weight *= self.last_decay
        for name, value in model.state_dict().items():
            shadow = self.shadow[name]
            if value.dtype.is_floating_point:
                shadow.mul_(self.last_decay).add_(value.detach(), alpha=1 - self.last_decay)
            else:
                shadow.copy_(value.detach())
