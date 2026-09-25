"""PPO actor fed a frozen deployable student latent; privileged critic only.

Environment observation: legacy137, student16. SAPG appends its coefficient ID.
Only legacy137 is normalized, exactly as in the distilled policy. Existing
teacher parameter names/shapes remain load-compatible; its unused actor-side
privileged encoder is frozen and is never called by this actor.
"""
import copy
import torch
from rl_games.algos_torch import models
from .a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder


class WujiFixedStudentBuilder(A2CSAPGPrivBuilder):
    class Network(A2CSAPGPrivBuilder.Network):
        def __init__(self, params, **kwargs):
            super().__init__(params, **kwargs)
            assert self.original_input_shape == 138 and self.pid_idx == 137
            assert self.base_obs_dim == 132 and self.policy_obs_dim == 111
            assert self.privileged_latent_dim == 16 and self.separate
            for parameter in self.priv_encoder.parameters():
                parameter.requires_grad_(False)

        def _extract_parts(self, raw_obs):
            return super()._extract_parts(raw_obs[:, :138])

        def _fuse_actor_inputs(self, raw_obs):
            # Never invoke the privileged encoder or read privileged/contact
            # columns. The final16 are computed from2055 student inputs.
            policy, _, _, exploration = self._extract_parts(raw_obs)
            latent = raw_obs[:, 138:154]
            assert latent.shape[1] == 16
            self.last_privileged_latent = latent
            return torch.cat([policy, latent, exploration], dim=1)

        def forward(self, obs_dict):
            raw = obs_dict['obs']
            assert raw.shape[1] == 154
            reordered = dict(obs_dict)
            reordered['obs'] = torch.cat([raw[:, :137], raw[:, 153:154], raw[:, 137:153]], dim=1)
            return super().forward(reordered)

    def build(self, name, **kwargs):
        return self.Network(self.params, **kwargs)


class WujiFixedStudentModel(models.ModelA2CContinuousLogStd):
    def build(self, config):
        assert tuple(config['input_shape']) == (154,) and config['coef_id_idx'] == 153
        original = copy.deepcopy(config)
        original.update(input_shape=(138,), coef_id_idx=137)
        network = self.network_builder.build(self.model_class, **original)
        return self.Network(network, obs_shape=(154,), normalize_value=config.get('normalize_value', False),
                            normalize_input=config.get('normalize_input', False),
                            value_size=config.get('value_size', 1), extra_info_start_idx=137)

    class Network(models.ModelA2CContinuousLogStd.Network):
        def train(self, mode=True):
            super().train(mode)
            if self.normalize_input:
                self.running_mean_std.eval()
            return self


def register_models():
    from rl_games.algos_torch import model_builder
    model_builder.register_network('wuji_fixed_student_actor', WujiFixedStudentBuilder)
    model_builder.register_model('continuous_a2c_wuji_fixed_student', WujiFixedStudentModel)
