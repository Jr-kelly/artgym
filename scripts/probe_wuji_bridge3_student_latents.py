"""Compare two student encoders on shared, physically executed trajectories.

The chosen driver alone advances physics, RNN state and RNG. Counterfactual
teacher/student actions use that same incoming RNN state and are discarded.
These are development diagnostics, not additional blind validation trials.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import wuji_goal_common  # Import Isaac Gym before torch.
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.audit_distillation_runtime import tensor_digest
from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
from isaacgymenvs.eval_common import preprocess_train_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--plain-student', type=Path, required=True)
    parser.add_argument('--controller-student', type=Path, required=True)
    parser.add_argument('--initial-states', type=Path, required=True)
    parser.add_argument('--initial-state-rows', type=int, nargs='+', required=True)
    parser.add_argument('--driver', choices=['teacher', 'plain', 'controller'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261057)
    parser.add_argument('--driver-only', action='store_true',
                        help='Skip counterfactual calls to check exact physical/RNN noninterference.')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).read_bytes()
    (args.output / 'probe_source.py').write_bytes(source)
    teacher_hash = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    original_make = wuji_goal_common.make_player
    frames, refs = [], []
    metadata = dict(driver=args.driver, driver_only=args.driver_only,
                    source_sha256=hashlib.sha256(source).hexdigest(),
                    teacher_sha256=teacher_hash, students={}, seed=args.seed)

    def make_player(cfg, checkpoint):
        env, player = original_make(cfg, checkpoint)
        env.set_student_encoder_obs_enabled(True)
        assert env.student_obs_dim == 2076 and env.proprio_obs_dim == 40
        network = player.model.a2c_network
        teacher = network.priv_encoder
        assert not teacher.training
        encoders = {'teacher': teacher}
        refs.append(player.model)
        metadata['model_before'] = tensor_digest(player.model.state_dict())
        for label, path, expected_task, expected_dim in [
            ('plain', args.plain_student, 'wuji_acquisition_bridge3_hemisphere', 2055),
            ('controller', args.controller_student, 'wuji_acquisition_bridge3_controller_state', 2076),
        ]:
            artifact = torch.load(path, map_location='cpu')
            meta = artifact['distill_meta']
            assert meta['teacher_checkpoint_sha256'] == teacher_hash
            assert meta['task'] == expected_task and meta['hand'] == 'wuji_paper_official_actuator'
            encoder, dim, proprio_dim, history_len = build_student_encoder_from_artifact(
                player, cfg, preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True)),
                artifact, meta)
            assert (dim, proprio_dim, history_len) == (expected_dim, 40, 50)
            encoder.eval()
            encoders[label] = encoder
            metadata['students'][label] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                               dim=dim, state_before=tensor_digest(encoder.state_dict()))
        refs.append(encoders)
        original = player.get_action

        def observed(obs, is_deterministic=False, **kwargs):
            assert is_deterministic
            incoming = [v.clone() for v in player.states] if player.is_rnn else None
            cpu_rng = torch.get_rng_state()
            gpu_rng = torch.cuda.get_rng_state(player.device)
            inputs = env.get_student_encoder_observations()
            base = torch.cat([env.proprioception_buf.reshape(env.num_envs, -1), env._get_init_obs()], -1)
            assert torch.equal(inputs[:, :2055], base)
            assert torch.equal(inputs[:, -21:], env.current_controller_features())
            outputs, latents = {}, {}
            chosen_states = chosen_cpu_rng = chosen_gpu_rng = None
            labels = [args.driver] + ([] if args.driver_only else [x for x in encoders if x != args.driver])
            try:
                with torch.no_grad():
                    for label in labels:
                        if player.is_rnn:
                            player.states = [v.clone() for v in incoming]
                        torch.set_rng_state(cpu_rng)
                        torch.cuda.set_rng_state(gpu_rng, player.device)
                        network.priv_encoder = encoders[label]
                        network.actor_encoder_obs_override = (None if label == 'teacher' else
                                                               inputs[:, :2055] if label == 'plain' else inputs)
                        outputs[label] = original(obs, is_deterministic=True, **kwargs).detach().clone()
                        latents[label] = network.last_privileged_latent.detach().clone()
                        if label == args.driver:
                            chosen_states = [v.clone() for v in player.states] if player.is_rnn else None
                            chosen_cpu_rng = torch.get_rng_state()
                            chosen_gpu_rng = torch.cuda.get_rng_state(player.device)
            finally:
                network.priv_encoder = teacher
                network.actor_encoder_obs_override = None
                if chosen_cpu_rng is not None:
                    player.states = chosen_states
                    torch.set_rng_state(chosen_cpu_rng)
                    torch.cuda.set_rng_state(chosen_gpu_rng, player.device)
                    network.last_privileged_latent = latents[args.driver]
            row = dict(active=env.eval_active_mask, driver_action=outputs[args.driver],
                       issued_targets=env.cur_targets[:, :20], controller_features=inputs[:, -21:])
            for label in labels:
                row[label + '_action'] = outputs[label]
                row[label + '_latent'] = latents[label]
            if player.is_rnn:
                # Small checksums make exact driver-only comparison possible
                # without serializing the entire recurrent state at each step.
                row['driver_rnn_sums'] = torch.stack([v.double().sum((0, 2)) for v in chosen_states], -1)
            frames.append({key: value.detach().cpu().numpy().copy() for key, value in row.items()})
            return outputs[args.driver]

        player.get_action = observed
        return env, player

    wuji_goal_common.make_player = make_player
    # Import after installing the factory; its imported reference is captured.
    from scripts import audit_wuji_timed_commands
    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], '--checkpoint', str(args.checkpoint), '--initial-states', str(args.initial_states),
                    '--initial-state-rows'] + [str(x) for x in args.initial_state_rows] + [
                    '--task', 'wuji_acquisition_bridge3_controller_state', '--hand', 'wuji_paper_official_actuator',
                    '--object', 'knife_wuji_bridge3_20260922', '--stage-seconds', '2', '--seed', str(args.seed),
                    '--output', str(args.output)]
        audit_wuji_timed_commands.main()
    finally:
        sys.argv = old_argv
        wuji_goal_common.make_player = original_make
        audit_wuji_timed_commands.make_player = original_make
    metadata['model_after'] = tensor_digest(refs[0].state_dict())
    assert metadata['model_before'] == metadata['model_after']
    for label in ['plain', 'controller']:
        after = tensor_digest(refs[1][label].state_dict())
        assert after == metadata['students'][label]['state_before']
        metadata['students'][label]['state_after'] = after
    trace = {key: np.stack([row[key] for row in frames]) for key in frames[0]}
    assert trace['active'].shape == (600, len(args.initial_state_rows))
    np.savez_compressed(args.output / 'encoder_error_trace.npz', **trace)
    summaries = []
    if not args.driver_only:
        row_ids = np.asarray(args.initial_state_rows)
        for grasp, low, high in [('source', 0, 100), ('row16', 100, 200), ('row15', 200, 300), ('heldout', 300, 332)]:
            selected = (row_ids >= low) & (row_ids < high)
            if not selected.any():
                continue
            for stage in range(10):
                sl = slice(stage * 60, (stage + 1) * 60)
                active = trace['active'][sl, selected]
                for label in ['plain', 'controller']:
                    latent_error = (trace[label + '_latent'] - trace['teacher_latent'])[sl, selected][active]
                    action_error = (trace[label + '_action'] - trace['teacher_action'])[sl, selected][active]
                    summaries.append(dict(grasp=grasp, stage=stage, student=label, active_transitions=int(active.sum()),
                        latent_mse=float(np.mean(latent_error ** 2)) if len(latent_error) else None,
                        support_action_mae=float(np.mean(abs(action_error[:, :16]))) if len(action_error) else None,
                        thumb_action_mae=float(np.mean(abs(action_error[:, 16:]))) if len(action_error) else None,
                        thumb_step_error_mrad=float(np.mean(abs(action_error[:, 16:]))) * 25 if len(action_error) else None))
    metadata.update(status='completed', scope=__doc__, steps=len(frames), num_envs=len(args.initial_state_rows),
                    initial_state_rows=args.initial_state_rows, summaries=summaries,
                    driver_note='report.json scores the specified driver; no counterfactual action reached physics')
    report_path = args.output / 'report.json'
    report = json.loads(report_path.read_text())
    report.update(probe_driver=args.driver, probe_source_sha256=metadata['source_sha256'],
                  probe_driver_only=args.driver_only,
                  student_sha256=None if args.driver == 'teacher' else metadata['students'][args.driver]['sha256'],
                  execution_scope=metadata['driver_note'])
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'encoder_report.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({k: v for k, v in metadata.items() if k != 'summaries'}), flush=True)


if __name__ == '__main__':
    main()
