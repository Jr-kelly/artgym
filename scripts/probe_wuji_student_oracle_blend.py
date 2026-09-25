"""Diagnose student latent error using explicitly privileged oracle interpolation.

Alpha0 is the unchanged student. Alpha1 substitutes the exact teacher latent
at every current physical state. Intermediate alphas use privileged information
and are diagnostic policies, never deployment or student success evidence.
The original fixed-clock physical evaluator and scoring remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import torch
import torch.nn as nn
from isaacgymenvs.distill import normalize_obs_slice
from isaacgymenvs import infer_student_impl
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--student-artifact', type=Path, required=True)
    parser.add_argument('--initial-states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--teacher-fraction', type=float, choices=[0., .5, 1.], required=True)
    parser.add_argument('--stage-seconds', type=int, choices=[2, 5], required=True)
    parser.add_argument('--seed', type=int, default=20261048)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output / 'report.json').exists()
    assert hashlib.sha256(args.student_artifact.read_bytes()).hexdigest() == '7afa3e41d1574e09b4cc6519e6af502ea598d6885d75b8318f0b30b27f6ef9b0'
    make_player = wuji_goal_common.make_player
    build_student = infer_student_impl.build_student_encoder_from_artifact
    captured = {}

    def capture_player(*arguments, **keywords):
        env, player = make_player(*arguments, **keywords)
        captured.update(env=env, player=player, teacher=player.model.a2c_network.priv_encoder)
        return env, player

    class OracleBlend(nn.Module):
        def __init__(self, student, teacher):
            super().__init__()
            self.student = student
            self.teacher = teacher
            self.calls = 0
            self.squared_error_sum = 0.
            self.elements = 0

        def forward(self, observations):
            env, player = captured['env'], captured['player']
            predicted = self.student(observations)
            truth = self.teacher(normalize_obs_slice(player.model, env.get_teacher_encoder_observations(), env.policy_obs_dim))
            assert predicted.shape == truth.shape and torch.isfinite(predicted).all() and torch.isfinite(truth).all()
            self.calls += 1
            self.squared_error_sum += float((predicted - truth).square().sum())
            self.elements += predicted.numel()
            if args.teacher_fraction == 0.:
                return predicted
            if args.teacher_fraction == 1.:
                return truth
            return (1. - args.teacher_fraction) * predicted + args.teacher_fraction * truth

    def wrapped_student(*arguments, **keywords):
        result = build_student(*arguments, **keywords)
        encoder = OracleBlend(result[0], captured['teacher'])
        captured['blend'] = encoder
        # The evaluator subsequently installs this encoder in the frozen actor.
        return (encoder,) + tuple(result[1:])

    wuji_goal_common.make_player = capture_player
    infer_student_impl.build_student_encoder_from_artifact = wrapped_student
    from scripts import audit_wuji_timed_commands
    evaluate = audit_wuji_timed_commands.run_grasp_evaluation_loop

    def audited_loop(player, env, **kwargs):
        before = tensor_digest(player.model.state_dict())
        result = evaluate(player, env, **kwargs)
        assert before == tensor_digest(player.model.state_dict())
        captured['model_frozen'] = True
        return result

    audit_wuji_timed_commands.run_grasp_evaluation_loop = audited_loop
    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], '--checkpoint', str(args.checkpoint), '--student-artifact', str(args.student_artifact),
                    '--initial-states', str(args.initial_states), '--output', str(args.output),
                    '--task', 'wuji_acquisition_official_timed2', '--hand', 'wuji_paper_official_actuator',
                    '--object', 'knife_wuji_precision_near01', '--stage-seconds', str(args.stage_seconds), '--seed', str(args.seed)]
        audit_wuji_timed_commands.main()
    finally:
        sys.argv = old_argv
        wuji_goal_common.make_player = make_player
        infer_student_impl.build_student_encoder_from_artifact = build_student
        audit_wuji_timed_commands.run_grasp_evaluation_loop = evaluate
    blend = captured['blend']
    assert blend.calls == 600 and captured['model_frozen']
    metadata = dict(scope=__doc__, teacher_fraction=args.teacher_fraction,
                    uses_privileged_oracle=args.teacher_fraction > 0,
                    model_unchanged=True, physical_control_steps=blend.calls,
                    latent_mse_on_actual_closed_loop_states=blend.squared_error_sum / blend.elements,
                    checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                    student_sha256=hashlib.sha256(args.student_artifact.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output / 'oracle-blend-source.py').write_bytes(Path(__file__).read_bytes())
    (args.output / 'oracle-blend-report.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata), flush=True)


if __name__ == '__main__':
    main()
