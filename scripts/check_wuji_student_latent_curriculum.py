"""Verify training-only latent mixtures against explicit frozen-latent actions.

The alpha=0 path must equal pure student deployment. The alpha=1 path must
equal the original teacher. Same incoming actor RNN, exactly one retained
outgoing state, no surviving supervision hook, and unchanged model tensors.
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
from isaacgymenvs.distill import normalize_obs_slice, reset_done_rnn_states
from isaacgymenvs.utils.distill_rollout_utils import distillation_action, teacher_mix_fraction
from scripts.audit_distillation_runtime import tensor_digest


class ExplicitLatent(torch.nn.Module):
    def __init__(self, latent):
        super().__init__()
        self.latent = latent

    def forward(self, observations):
        return self.latent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    assert not (args.output / 'report.json').exists()
    root = Path(__file__).resolve().parents[1]
    cp = root / 'runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    artifact = root / 'runs/wuji-goal/frozen-candidates/student-near5cp50-teacher500-update500/student.pth'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == '7afa3e41d1574e09b4cc6519e6af502ea598d6885d75b8318f0b30b27f6ef9b0'
    cfg = configuration('wuji_acquisition_official_timed2', 32,
        ['hand=wuji_paper_official_actuator', 'object=knife_wuji_precision_near01'],
        train='wujiAcquisitionSAPG', seed=20261050)
    env, player = make_player(cfg, cp)
    network = player.model.a2c_network
    teacher = network.priv_encoder
    payload = torch.load(artifact, map_location='cpu')
    student, *_ = build_student_encoder_from_artifact(player, cfg,
        preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True)), payload, payload['distill_meta'])
    network.priv_encoder = student
    player.model.eval()
    for parameter in player.model.parameters():
        parameter.requires_grad_(False)
    for parameter in student.parameters():
        parameter.requires_grad_(True)
    student.train()
    env.set_student_encoder_obs_enabled(True)
    before = tensor_digest(player.model.state_dict())
    teacher_before = tensor_digest(teacher.state_dict())
    records = []
    try:
        obs = player.env_reset(player.env)
        for step in range(8):
            incoming = [v.clone() for v in player.states]
            proprio = env.get_student_encoder_observations()
            with torch.no_grad():
                truth = teacher(normalize_obs_slice(player.model, env.get_teacher_encoder_observations(), env.policy_obs_dim))
                student.eval()
                predicted = student(proprio)
                student.train()
                fractions = [1.0, 0.0, teacher_mix_fraction(step, .5, 4)]
                for fraction in fractions:
                    player.states = [v.clone() for v in incoming]
                    candidate = distillation_action(player, obs, proprio, teacher, False, True,
                        student_eval_mode=True, teacher_fraction=fraction, teacher_latent=truth)
                    outgoing = [v.clone() for v in player.states]
                    assert student.training and not student._forward_hooks
                    assert not hasattr(network, '_distillation_teacher_fraction')
                    player.states = [v.clone() for v in incoming]
                    if fraction == 1.0:
                        network.priv_encoder = teacher
                        network.actor_encoder_obs_override = None
                    else:
                        explicit = predicted if fraction == 0.0 else (1-fraction)*predicted+fraction*truth
                        network.priv_encoder = ExplicitLatent(explicit)
                        network.actor_encoder_obs_override = proprio
                    reference = player.get_action(obs, is_deterministic=True)
                    network.priv_encoder = student
                    network.actor_encoder_obs_override = None
                    assert torch.equal(reference, candidate), float((reference-candidate).abs().max())
                    assert all(torch.equal(a, b) for a, b in zip(outgoing, player.states))
            # No mixture in supervision: exact raw encoder output, nonzero
            # student gradient, no actor/teacher gradients or weight updates.
            student.zero_grad(set_to_none=True)
            raw = student(proprio)
            loss = (raw-truth).square().mean()
            loss.backward()
            gradients = [p.grad for p in student.parameters() if p.grad is not None]
            norm = float(torch.sqrt(sum(g.square().sum() for g in gradients)))
            assert norm > 0 and all(torch.isfinite(g).all() for g in gradients)
            assert all(p.grad is None for name, p in player.model.named_parameters()
                       if not name.startswith('a2c_network.priv_encoder.'))
            assert all(p.grad is None for p in teacher.parameters())
            records.append(dict(step=step, fraction=fractions[-1], gradient_norm=norm, max_action_error=0.0))
            obs, _, done, _ = player.env_step(player.env, reference)
            reset_done_rnn_states(player, done)
        assert before == tensor_digest(player.model.state_dict())
        assert teacher_before == tensor_digest(teacher.state_dict())
        assert [row['fraction'] for row in records] == [.5, .375, .25, .125, 0., 0., 0., 0.]
        sources = ['scripts/check_wuji_student_latent_curriculum.py', 'isaacgymenvs/utils/distill_rollout_utils.py',
                   'isaacgymenvs/distill.py', 'scripts/audit_distillation_runtime.py']
        report = dict(status='passed', scope=__doc__, physics_transitions=256, records=records,
            action_and_rnn_exact=True, supervision_hook_removed=True, model_tensors_unchanged=True,
            pure_student_after_schedule=True,
            sources={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources})
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
