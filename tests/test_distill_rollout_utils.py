import unittest
from types import SimpleNamespace
from isaacgymenvs.utils.distill_rollout_utils import distillation_action


class RolloutSelectionTest(unittest.TestCase):
    def test_policy_identity_single_rnn_step_and_restore(self):
        teacher, student, old_override, obs = object(), object(), object(), object()
        network = SimpleNamespace(priv_encoder=student, actor_encoder_obs_override=old_override)
        player = SimpleNamespace(model=SimpleNamespace(a2c_network=network))
        calls = []

        def action(*args, **kwargs):
            calls.append((network.priv_encoder, network.actor_encoder_obs_override))
            return len(calls)

        player.get_action = action
        self.assertEqual(distillation_action(player, None, obs, teacher, True, True), 1)
        self.assertEqual(calls[-1], (teacher, None))
        self.assertIs(network.priv_encoder, student)
        self.assertIs(network.actor_encoder_obs_override, old_override)
        self.assertEqual(distillation_action(player, None, obs, teacher, False, True), 2)
        self.assertEqual(calls[-1], (student, obs))
        self.assertIs(network.priv_encoder, student)
        self.assertIs(network.actor_encoder_obs_override, old_override)

    def test_failed_inference_restores_student(self):
        teacher, student = object(), object()
        network = SimpleNamespace(priv_encoder=student, actor_encoder_obs_override=None)
        def fail(*args, **kwargs):
            raise RuntimeError('inference failed')
        player = SimpleNamespace(model=SimpleNamespace(a2c_network=network), get_action=fail)
        with self.assertRaises(RuntimeError):
            distillation_action(player, None, None, teacher, True, True)
        self.assertIs(network.priv_encoder, student)
        self.assertIsNone(network.actor_encoder_obs_override)
