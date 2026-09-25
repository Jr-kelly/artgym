"""Audit actual rollout population and retained parameter rows around PPO."""
import os
from pathlib import Path
from scripts import wuji_goal_common
import torch
from rl_games.algos_torch.a2c_continuous import A2CAgent
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now
from isaacgymenvs.learning.wuji_population_student_actor import register_model


def main():
    register_model()
    from scripts.train_wuji_student_actor_audited import main as train
    output = Path(os.environ['WUJI_FIXED_STUDENT_AUDIT'])
    output.mkdir(parents=True, exist_ok=True)
    assert not (output/'population-audit.json').exists()
    original = A2CAgent.get_action_values
    agents = {}

    def observed(self, observation, rnn_states=None):
        requested = self.model.requested_population_ids
        count = self.num_actors // self.intr_coef_block_size
        assert count == len(requested) and count in [1, 5]
        assert float(self.config['off_policy_ratio']) == 0.
        actual = observation['obs'][:, -1]
        expected = self.intr_reward_coef_embd[:, 0]
        assert torch.equal(actual, expected)
        assert torch.equal(torch.unique(actual).sort()[0], torch.tensor(requested, device=actual.device).sort()[0])
        if id(self) not in agents:
            model = self.model.state_dict()
            agents[id(self)] = dict(agent=self, calls=0, transitions=0, population=count,
                first_model_sha256=tensor_digest(model),
                retained_before={k:model[k].detach().clone() for k in ['a2c_network.sigma', 'a2c_network.extra_params']})
        record = agents[id(self)]
        record['calls'] += 1
        record['transitions'] += self.num_actors
        return original(self, observation, rnn_states)

    A2A = A2CAgent
    A2A.get_action_values = observed
    returned = False
    try:
        train()
        returned = True
    finally:
        A2A.get_action_values = original
        rows = []
        for record in agents.values():
            agent = record['agent']
            model = agent.model.state_dict()
            retained = {}
            for key, before in record['retained_before'].items():
                retained[key] = dict(unused_rows_unchanged=torch.equal(before[1:], model[key][1:]),
                    first_row_changed=not torch.equal(before[0], model[key][0]))
                if record['population'] == 1:
                    assert retained[key]['unused_rows_unchanged']
            rows.append(dict(population=record['population'], rollout_calls=record['calls'],
                rollout_transitions=record['transitions'], actual_input_ids=agent.model.requested_population_ids,
                first_model_sha256=record['first_model_sha256'], parameter_rows=retained,
                intrinsic_coefficients=agent.intr_reward_coef[::agent.intr_coef_block_size].tolist()))
        atomic_json(output/'population-audit.json', dict(training_returned=returned, finished=now(), records=rows))
        if returned:
            assert len(rows) == 1 and rows[0]['rollout_transitions'] > 0


if __name__ == '__main__':
    main()
