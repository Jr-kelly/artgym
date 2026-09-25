"""Same-transition reward counterfactual; does not assume deterministic PhysX reruns."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from scripts import check_wuji_student_actor_runtime as runtime
from scripts.monitor_wuji_checkpoints import atomic_json, now
from isaacgymenvs.tasks.wuji_fixed_student_actor import WujiFixedStudentActor
import torch

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'runs/wuji-goal/diagnostics/student-actorrl-broad5-runtime-v2'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    assert not (OUTPUT/'status.json').exists()
    atomic_json(OUTPUT/'status.json', dict(status='running', started=now()))
    original = WujiFixedStudentActor.compute_reward
    checks = dict(transitions=0, state_tensor_comparisons=0, command_switches=0,
                  reward_delta_max_error=0.0)

    def counterfactual(self, actions):
        # Reward and clock updates do not call PhysX setters in this training
        # task. Save every top-level tensor (including simulator views), extras
        # and RNG, then replay only the reward computation from the same state.
        assert not self.eval_mode
        before = {k:v.clone() for k,v in vars(self).items() if torch.is_tensor(v)}
        extras = copy.deepcopy(self.extras)
        cpu_rng = torch.get_rng_state()
        cuda_rng = torch.cuda.get_rng_state(self.device)
        coefficient = self.cfg['env']['broadGoalReward']['coefficient']
        assert coefficient == 5
        self.cfg['env']['broadGoalReward']['coefficient'] = 0.0
        original(self, actions)
        zero = {k:v.clone() for k,v in vars(self).items() if torch.is_tensor(v)}
        zero_extras = copy.deepcopy(self.extras)
        zero_extras.pop('BroadGoalReward', None)
        zero_cpu_rng = torch.get_rng_state()
        zero_cuda_rng = torch.cuda.get_rng_state(self.device)
        assert set(before) == set(zero)
        for name, value in before.items():
            current = getattr(self, name)
            if not torch.equal(current, value):
                current.copy_(value)
        self.extras = extras
        torch.set_rng_state(cpu_rng)
        torch.cuda.set_rng_state(cuda_rng, self.device)
        self.cfg['env']['broadGoalReward']['coefficient'] = coefficient
        original(self, actions)
        assert torch.equal(torch.get_rng_state(), zero_cpu_rng)
        assert torch.equal(torch.cuda.get_rng_state(self.device), zero_cuda_rng)
        for name, value in zero.items():
            if name != 'rew_buf':
                assert torch.equal(getattr(self, name), value), name
                checks['state_tensor_comparisons'] += 1
        assert set(self.extras) == set(zero_extras)|{'BroadGoalReward'}
        for name, value in zero_extras.items():
            if torch.is_tensor(value):
                assert torch.equal(self.extras[name], value), name
        error = torch.norm(before['obj_dof_pos']-before['goal_obj_dof_pos'], p=1, dim=-1)
        valid = ~before['truncated_envs'] & torch.isfinite(error)
        expected = torch.where(valid, 5*torch.exp(-(error/.01).square()), torch.zeros_like(error))
        delta = self.rew_buf-zero['rew_buf']
        assert torch.allclose(delta, expected, atol=2e-5, rtol=2e-5)
        checks['reward_delta_max_error'] = max(checks['reward_delta_max_error'], float((delta-expected).abs().max()))
        checks['command_switches'] += int((before['goal_obj_dof_pos'] != self.goal_obj_dof_pos).any(-1).sum())
        checks['transitions'] += self.num_envs

    WujiFixedStudentActor.compute_reward = counterfactual
    previous_args = sys.argv
    try:
        sys.argv = [previous_args[0], '--output', str(OUTPUT/'runtime'), '--steps', '600',
                    '--broad-goal-coefficient', '5']
        runtime.main()
        assert checks['transitions'] == 19200 and checks['command_switches'] > 0
        report = json.loads((OUTPUT/'runtime/report.json').read_text())
        sources = report['sources']
        sources[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        atomic_json(OUTPUT/'report.json', dict(status='passed', finished=now(), sources=sources,
                    checks=checks, runtime=report, same_state_reward_only_effect=True,
                    physics_steps=600, actual_physics_transitions=19200,
                    no_extra_physics_for_counterfactual=True,
                    previous_failed_gate='student-actorrl-broad5-runtime-v1',
                    limitation='Independent PhysX trajectories were not bitwise equal; no claim that different reward branches have identical across-process physical trajectories.'))
        atomic_json(OUTPUT/'status.json', dict(status='completed', returncode=0, finished=now()))
    except BaseException as error:
        atomic_json(OUTPUT/'status.json', dict(status='failed', error=repr(error), finished=now()))
        raise
    finally:
        sys.argv = previous_args
        WujiFixedStudentActor.compute_reward = original


if __name__ == '__main__':
    main()
