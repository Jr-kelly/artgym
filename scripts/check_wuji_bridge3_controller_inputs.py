"""Exercise added controller inputs without privileged student observations."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
from scripts.audit_distillation_runtime import tensor_digest
import torch
from omegaconf import OmegaConf
from isaacgymenvs.tasks.wuji_bridge3_hemisphere import WujiBridge3Hemisphere
from isaacgymenvs.tasks.wuji_bridge3_controller_state import controller_state_features
from isaacgymenvs.distill import reset_done_rnn_states


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    root = Path(__file__).resolve().parents[1]
    cp = root/'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth'
    assert hashlib.sha256(cp.read_bytes()).hexdigest() == '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
    cfg = configuration('wuji_acquisition_bridge3_controller_state', 64,
                        ['hand=wuji_paper_official_actuator', 'object=knife_wuji_bridge3_20260922',
                         'test=False', '+task.env.enableStudentEncoderObs=True'], train='wujiAcquisitionSAPG', seed=20261057)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, cp)
    before = tensor_digest(player.model.state_dict())
    try:
        player.model.eval()
        obs = player.env_reset(player.env)
        assert env.student_obs_dim == 2076 and env.proprio_obs_dim == 40
        assert env.proprio_history_len == 50 and env.policy_obs_dim == 111
        assert env.privileged_obs_dim == 21 and env.student_temporal_obs_layout['init_dim'] == 76
        command_values = set()
        for step in range(180):
            student = env.get_student_encoder_observations()
            base = torch.cat([env.proprioception_buf.reshape(env.num_envs, -1), env._get_init_obs()], -1)
            assert torch.equal(student[:, :2055], base)
            issued = env.cur_targets[:, :20].clone()
            command = (env.goal_obj_dof_pos-env.init_obj_dof_pos).clone()
            expected = controller_state_features(issued, env.hand_dof_lower_limits, env.hand_dof_upper_limits, command, .04)
            assert torch.equal(student[:, -21:], expected)
            assert torch.isfinite(student).all()
            assert torch.allclose((expected[:, :20]+1)*.5*(env.hand_dof_upper_limits-env.hand_dof_lower_limits)+env.hand_dof_lower_limits,
                                  issued, atol=2e-7, rtol=1e-6)
            command_values.update(round(float(x), 3) for x in command.flatten())
            inherited = WujiBridge3Hemisphere._compute_sapg_priv_observations(env)
            actual = env._compute_sapg_priv_observations()
            assert all(torch.equal(x,y) for x,y in zip(actual, inherited))
            with torch.no_grad():
                action = player.get_action(obs, is_deterministic=True)
            obs, _, done, _ = player.env_step(player.env, action)
            reset_done_rnn_states(player, done)
        assert command_values == {0., .04}, command_values
        assert tensor_digest(player.model.state_dict()) == before
        sources = ['scripts/check_wuji_bridge3_controller_inputs.py',
                   'isaacgymenvs/tasks/wuji_bridge3_controller_state.py',
                   'isaacgymenvs/cfg/task/wuji_acquisition_bridge3_controller_state.yaml',
                   'scripts/distill_wuji_variable_student.py']
        report = dict(status='passed', transitions=180*64, scope=__doc__,
                      unchanged_teacher_observations=True, frozen_teacher_unchanged=True,
                      existing_history_contains='Measured joint angles AND historical actions,40values/frame',
                      added_student_inputs='Current20issued joint targets,1externally commanded slider offset',
                      current_privileged_object_inputs=False, controller_mapping_exact=True,
                      existing_student_input_prefix_exact=True, command_values=sorted(command_values),
                      sources={s: hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources})
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        (args.output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        print(json.dumps(report))
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
