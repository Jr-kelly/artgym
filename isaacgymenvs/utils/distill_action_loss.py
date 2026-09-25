"""Optional action-aware latent distillation through the frozen actor.

Both counterfactual means use the same incoming detached RNN state. Neither
counterfactual changes the live policy state or drives physics. Raw Gaussian
means are matched, avoiding zero gradients at output clipping. Deployment uses
the unchanged student encoder and frozen actor.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class _GivenLatent(nn.Module):
    def __init__(self, latent):
        super().__init__()
        self.latent = latent

    def forward(self, observation):
        assert observation.shape[0] == self.latent.shape[0]
        return self.latent


def frozen_actor_mean(player, observations, latent, incoming_states):
    network = player.model.a2c_network
    encoder = network.priv_encoder
    override = network.actor_encoder_obs_override
    previous_latent = network.last_privileged_latent
    assert not player.model.training, 'Action distillation requires frozen evaluation-mode normalization'
    obs = player.model.norm_obs(player._preproc_obs(observations))
    state = [v.detach().clone() for v in incoming_states] if incoming_states is not None else None
    recurrent = [module for module in network.modules() if isinstance(module, nn.RNNBase)]
    assert all(module.dropout == 0 for module in recurrent), 'Counterfactual training-mode RNN requires zero dropout'
    recurrent_modes = [module.training for module in recurrent]
    try:
        network.priv_encoder = _GivenLatent(latent)
        network.actor_encoder_obs_override = None
        # cuDNN needs a training-mode reserve buffer for backward. Enable it
        # only on zero-dropout RNN leaves; frozen normalizers remain in eval.
        # This also retains the inference kernel's arithmetic, unlike the
        # native LSTM path whose observed H100 parity error exceeded 5e-5.
        for module in recurrent:
            module.training = True
        result = network(dict(obs=obs, rnn_states=state, seq_length=1))
        return result[0]
    finally:
        for module, training in zip(recurrent, recurrent_modes):
            module.training = training
        network.priv_encoder = encoder
        network.actor_encoder_obs_override = override
        network.last_privileged_latent = previous_latent


def distillation_action_loss(player, observations, student_latent, teacher_latent, incoming_states):
    student_mean = frozen_actor_mean(player, observations, student_latent, incoming_states)
    with torch.no_grad():
        teacher_mean = frozen_actor_mean(player, observations, teacher_latent, incoming_states)
    assert torch.isfinite(student_mean).all() and torch.isfinite(teacher_mean).all()
    return F.mse_loss(student_mean, teacher_mean), student_mean, teacher_mean
