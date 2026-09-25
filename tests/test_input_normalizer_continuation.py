"""Check selective freezing across repeated PPO train/eval mode transitions."""
from types import SimpleNamespace
import unittest

import torch
from torch import nn
from rl_games.common.a2c_common import A2CBase
from rl_games.algos_torch.running_mean_std import RunningMeanStd


class InputNormalizerContinuationTest(unittest.TestCase):
    def exercise(self, freeze):
        torch.manual_seed(829)
        model = nn.Module()
        model.running_mean_std = RunningMeanStd((3,))
        model.value_mean_std = RunningMeanStd((1,))
        model.actor = nn.Linear(3, 1)
        agent = SimpleNamespace(model=model, normalize_input=True,
                                normalize_rms_advantage=True,
                                advantage_mean_std=RunningMeanStd((1,)),
                                config={} if freeze is None else {'freeze_input_normalizer': freeze})
        model.running_mean_std(torch.arange(30).reshape(10, 3).float())
        initial = {k: v.clone() for k, v in model.state_dict().items()}
        optimizer = torch.optim.Adam(model.actor.parameters(), lr=.01)
        for _ in range(3):
            A2CBase.set_eval(agent)
            A2CBase.set_train(agent)
            self.assertTrue(model.actor.training)
            self.assertTrue(model.value_mean_std.training)
            self.assertTrue(agent.advantage_mean_std.training)
            optimizer.zero_grad()
            inputs = model.running_mean_std(torch.randn(8, 3) + 7)
            loss = (model.actor(inputs)-1).square().mean()
            loss.backward()
            self.assertTrue(torch.isfinite(model.actor.weight.grad).all())
            optimizer.step()
            model.value_mean_std(torch.randn(8, 1))
        result = model.state_dict()
        self.assertFalse(torch.equal(initial['actor.weight'], result['actor.weight']))
        self.assertGreater(float(result['value_mean_std.count']), float(initial['value_mean_std.count']))
        if freeze:
            for key in initial:
                if key.startswith('running_mean_std.'):
                    self.assertTrue(torch.equal(initial[key], result[key]), key)
        else:
            self.assertGreater(float(result['running_mean_std.count']), float(initial['running_mean_std.count']))
        return result

    def test_input_only_freezing_preserves_stats_and_learning(self):
        self.exercise(True)

    def test_default_and_explicit_false_match(self):
        default, adaptive = self.exercise(None), self.exercise(False)
        for key in default:
            self.assertTrue(torch.equal(default[key], adaptive[key]), key)

    def test_missing_normalizer_is_rejected(self):
        agent = SimpleNamespace(model=nn.Linear(3, 1), normalize_input=False,
                                config={'freeze_input_normalizer': True})
        with self.assertRaisesRegex(ValueError, 'normalize_input'):
            A2CBase.set_train(agent)


if __name__ == '__main__':
    unittest.main()
