"""Verify differentiable frozen-actor supervision against actual policy/physics."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
import torch
from omegaconf import OmegaConf
from isaacgymenvs.distill import normalize_obs_slice, reset_done_rnn_states
from isaacgymenvs.eval_common import preprocess_train_config
from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
from isaacgymenvs.utils.distill_action_loss import distillation_action_loss
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output / 'report.json').exists()
    root = Path(__file__).resolve().parents[1]
    cp = root / 'runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    artifact_path = root / 'runs/wuji-goal/frozen-candidates/student-near5cp50-teacher500-update500/student.pth'
    assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == '7afa3e41d1574e09b4cc6519e6af502ea598d6885d75b8318f0b30b27f6ef9b0'
    cfg = configuration('wuji_acquisition_official_timed2', 32,
                        ['hand=wuji_paper_official_actuator', 'object=knife_wuji_precision_near01'],
                        train='wujiAcquisitionSAPG', seed=20261040)
    env, player = make_player(cfg, cp)
    env.set_student_encoder_obs_enabled(True)
    player.model.eval()
    for param in player.model.parameters(): param.requires_grad_(False)
    artifact = torch.load(artifact_path, map_location='cpu')
    encoder, *_ = build_student_encoder_from_artifact(player, cfg,
        preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True)),
        artifact, artifact['distill_meta'])
    for param in encoder.parameters(): param.requires_grad_(True)
    encoder.train()
    before = tensor_digest(player.model.state_dict())
    encoder_before = tensor_digest(encoder.state_dict())
    optimizer = torch.optim.Adam(encoder.parameters(), lr=1e-4)
    maximum_parity_error, nonzero_gradients, losses = 0., [], []
    try:
        observations = player.env_reset(player.env)
        for _ in range(8):
            incoming = [v.detach().clone() for v in player.states]
            teacher_obs = normalize_obs_slice(player.model, env.get_teacher_encoder_observations(), env.policy_obs_dim)
            with torch.no_grad(): teacher_latent = player.model.a2c_network.priv_encoder(teacher_obs)
            student_latent = encoder(env.get_student_encoder_observations())
            action = player.get_action(observations, is_deterministic=True)
            outgoing = [v.clone() for v in player.states]
            optimizer.zero_grad(set_to_none=True)
            loss, student_mean, teacher_mean = distillation_action_loss(player, observations, student_latent, teacher_latent, incoming)
            assert all(torch.equal(a, z) for a, z in zip(outgoing, player.states)), 'Counterfactual advanced the live RNN'
            assert bool(torch.all(player.actions_low == -1)) and bool(torch.all(player.actions_high == 1))
            difference = float((teacher_mean.clamp(-1, 1)-action).abs().max())
            maximum_parity_error = max(maximum_parity_error, difference)
            assert difference < 5e-5, difference
            assert student_mean.requires_grad and not teacher_mean.requires_grad
            loss.backward()
            gradients = [p.grad for p in encoder.parameters() if p.grad is not None]
            assert gradients and all(torch.isfinite(g).all() for g in gradients)
            norm = float(torch.sqrt(sum((g*g).sum() for g in gradients)))
            assert norm > 0
            assert all(p.grad is None for p in player.model.parameters())
            nonzero_gradients.append(norm)
            losses.append(float(loss.detach()))
            torch.nn.utils.clip_grad_norm_(encoder.parameters(), 1.)
            optimizer.step()
            observations, _, done, _ = player.env_step(player.env, action)
            reset_done_rnn_states(player, done)
        assert tensor_digest(player.model.state_dict()) == before
        assert tensor_digest(encoder.state_dict()) != encoder_before
        sources = ['isaacgymenvs/utils/distill_action_loss.py', 'scripts/check_wuji_action_distillation.py',
                   'isaacgymenvs/distill.py', 'isaacgymenvs/learning/a2c_sapg_priv_network_builder.py']
        report = dict(status='passed', scope=__doc__, physics_transitions=256, model_before=before,
                      model_after=tensor_digest(player.model.state_dict()),
                      student_changed=True, teacher_actions_drove_physics=True,
                      live_rnn_not_advanced_by_counterfactual=True, max_teacher_mean_action_error=maximum_parity_error,
                      encoder_gradient_norms=nonzero_gradients, losses=losses,
                      sources={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources})
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
