"""Keep all five checkpoint rows while training one or five policy groups."""
import copy
import torch
from .wuji_fixed_student_actor import WujiFixedStudentModel


class WujiPopulationStudentModel(WujiFixedStudentModel):
    def build(self, config):
        requested = config['coef_ids']
        assert requested.ndim == 1 and len(requested) in [1, 5]
        expected = torch.linspace(50., 0., len(requested), device=requested.device)
        assert torch.equal(requested, expected)
        expanded = copy.deepcopy(config)
        expanded['coef_ids'] = torch.linspace(50., 0., 5, device=requested.device)
        model = super().build(expanded)
        model.requested_population_ids = requested.detach().cpu().tolist()
        assert torch.equal(model.a2c_network.param_ids, expanded['coef_ids'])
        assert torch.equal(model.a2c_network.sigma_ids, expanded['coef_ids'])
        # Every forward operation is the existing fixed-student implementation.
        # Unused checkpoint rows are retained for loading and original auditing.
        return model


def register_model():
    from rl_games.algos_torch import model_builder
    model_builder.register_model('continuous_a2c_wuji_population_student', WujiPopulationStudentModel)
