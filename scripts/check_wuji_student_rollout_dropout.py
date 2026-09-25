"""Measure encoder-dropout action randomness at fixed physics and RNN state.

The legacy rollout remains the default. The optional evaluation-mode rollout
must exactly match deployment, restore all module modes, and advance the live
RNN only once. Physical transitions use that deployment-equivalent action.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
import torch
from omegaconf import OmegaConf
from isaacgymenvs.eval_common import preprocess_train_config
from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
from isaacgymenvs.utils.distill_rollout_utils import distillation_action
from isaacgymenvs.distill import reset_done_rnn_states
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    assert not (args.output / 'report.json').exists()
    root = Path(__file__).resolve().parents[1]
    cp = root / 'runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    artifact_path = root / 'runs/wuji-goal/frozen-candidates/student-near5cp50-teacher500-update500/student.pth'
    cfg = configuration('wuji_acquisition_official_timed2', 32,
                        ['hand=wuji_paper_official_actuator', 'object=knife_wuji_precision_near01'],
                        train='wujiAcquisitionSAPG', seed=20261049)
    env, player = make_player(cfg, cp)
    teacher = player.model.a2c_network.priv_encoder
    payload = torch.load(artifact_path, map_location='cpu')
    encoder, *_ = build_student_encoder_from_artifact(player, cfg,
        preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True)), payload, payload['distill_meta'])
    player.model.a2c_network.priv_encoder = encoder
    player.model.eval()
    encoder.train()
    dropouts = [module for module in encoder.modules() if isinstance(module, torch.nn.Dropout)]
    assert len(dropouts) == 5 and all(module.p == .05 for module in dropouts)
    env.set_student_encoder_obs_enabled(True)
    digest = tensor_digest(player.model.state_dict())
    records = []
    try:
        obs = player.env_reset(player.env)
        for step in range(8):
            incoming = [v.clone() for v in player.states]
            student_obs = env.get_student_encoder_observations()
            repeated = {}
            for eval_mode in [False, True]:
                values = []
                for _ in range(4):
                    player.states = [v.clone() for v in incoming]
                    with torch.no_grad():
                        action = distillation_action(player, obs, student_obs, teacher, False, True,
                                                     student_eval_mode=eval_mode)
                    assert encoder.training and all(module.training for module in dropouts)
                    values.append(action.clone())
                stack = torch.stack(values)
                repeated[eval_mode] = float((stack - stack[0]).abs().max())
                if eval_mode:
                    assert torch.equal(stack, stack[0:1].expand_as(stack))
            # Compare the enabled path against normal deployment with the same
            # incoming state, retaining only the latter action's outgoing state.
            player.states = [v.clone() for v in incoming]
            with torch.no_grad():
                candidate = distillation_action(player, obs, student_obs, teacher, False, True, student_eval_mode=True)
            candidate_states = [v.clone() for v in player.states]
            player.states = [v.clone() for v in incoming]
            encoder.eval()
            player.model.a2c_network.actor_encoder_obs_override = student_obs
            deployment = player.get_action(obs, is_deterministic=True)
            assert torch.equal(candidate, deployment)
            assert all(torch.equal(a, b) for a, b in zip(candidate_states, player.states))
            player.model.a2c_network.actor_encoder_obs_override = None
            encoder.train()
            records.append(dict(step=step, legacy_max_repeat_action_error=repeated[False],
                                eval_mode_max_repeat_action_error=repeated[True], deployment_action_error=0.))
            obs, _, done, _ = player.env_step(player.env, deployment)
            reset_done_rnn_states(player, done)
        assert max(row['legacy_max_repeat_action_error'] for row in records) > 1e-3
        assert tensor_digest(player.model.state_dict()) == digest
        files = ['scripts/check_wuji_student_rollout_dropout.py', 'isaacgymenvs/utils/distill_rollout_utils.py']
        report = dict(status='passed', scope=__doc__, physics_transitions=256, dropout_p=.05,
                      dropout_layers=5, records=records, model_unchanged=True,
                      encoder_training_mode_restored=True, deployment_actions_and_rnn_match_exactly=True,
                      sources={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files})
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
