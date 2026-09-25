"""Zero-initialized controller residual keeps every inherited policy tensor."""
import copy
import torch
from .a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder
from .wuji_fixed_student_actor import WujiFixedStudentBuilder, WujiFixedStudentModel


class WujiControllerStudentBuilder(WujiFixedStudentBuilder):
    class Network(WujiFixedStudentBuilder.Network):
        def __init__(self, params, **kwargs):
            super().__init__(params, **kwargs)
            self.controller_enabled = bool(params['controller_adapter']['enabled'])
            self.controller_adapter = torch.nn.Linear(20, 16)
            torch.nn.init.zeros_(self.controller_adapter.weight)
            torch.nn.init.zeros_(self.controller_adapter.bias)

        def _fuse_actor_inputs(self, raw_obs):
            policy, _, _, exploration = self._extract_parts(raw_obs)
            features = raw_obs[:, 154:174]
            assert features.shape[1] == 20
            if not self.controller_enabled:
                features = torch.zeros_like(features)
            latent = raw_obs[:, 138:154] + self.controller_adapter(features)
            self.last_privileged_latent = latent
            return torch.cat([policy, latent, exploration], dim=1)

        def forward(self, obs_dict):
            raw = obs_dict['obs']
            assert raw.shape[1] == 174
            reordered = dict(obs_dict)
            reordered['obs'] = torch.cat([raw[:, :137], raw[:, 173:174], raw[:, 137:173]], dim=1)
            return A2CSAPGPrivBuilder.Network.forward(self, reordered)


class WujiControllerStudentModel(WujiFixedStudentModel):
    def build(self, config):
        assert tuple(config['input_shape']) == (174,) and config['coef_id_idx'] == 173
        original = copy.deepcopy(config)
        original.update(input_shape=(138,), coef_id_idx=137)
        network = self.network_builder.build(self.model_class, **original)
        return self.Network(network, obs_shape=(174,), normalize_value=config.get('normalize_value', False),
                            normalize_input=config.get('normalize_input', False),
                            value_size=config.get('value_size', 1), extra_info_start_idx=137)


def register_models():
    from rl_games.algos_torch import model_builder
    model_builder.register_network('wuji_controller_student_actor', WujiControllerStudentBuilder)
    model_builder.register_model('continuous_a2c_wuji_controller_student', WujiControllerStudentModel)
