"""Learner-state labels with recurrent experts following the actual history.

Handover mode is a scripted expert-availability diagnostic, never a unified
policy result. Behavior mode applies the same learner to all four sources.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from scripts import evaluate_wuji_recovery as audit
import numpy as np
import torch
from scripts.wuji_timed_command_metrics import score_timed_trace
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config, _infer_expl_num_blocks
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from omegaconf import OmegaConf


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, choices=[2, 5], required=True)
    parser.add_argument('--mode', choices=['behavior', 'handover'], required=True)
    parser.add_argument('--seed', type=int, default=2026093051)
    args = parser.parse_args()
    assert not args.output.exists()
    states = np.load(args.states)
    assert states.shape[0] == 128, '32 training initial states per source'
    n = 32
    expert_paths = [Path('runs/unified-policy-20260930/experts') / (name + '.pth')
                    for name in ['historical', 'source3']]
    rows, experts, metadata, raw_mu = [], [], {}, {}
    original_make = audit.make_player
    handover = round(args.seconds * 30 * .6)

    def make(cfg, checkpoint):
        env, player = original_make(cfg, checkpoint)
        config = preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True))
        for path in expert_paths:
            experts.append(build_policy_player(cfg, config, path, _infer_expl_num_blocks(path), 0))
        metadata.update(joint_lower=env.hand_dof_lower_limits.cpu().tolist(),
                        joint_upper=env.hand_dof_upper_limits.cpu().tolist())
        source3 = torch.arange(env.num_envs, device=player.device) >= 3 * n
        for index, expert in enumerate(experts):
            def capture(module, inputs, output, index=index):
                raw_mu[index] = output['mus'].detach().clone()
            expert.model.register_forward_hook(capture)
        get, step = player.get_action, player.env_step

        def action(obs, *positional, **kwargs):
            if not rows:
                for expert in experts:
                    init_player_rnn_for_batch(expert, env.num_envs)
            learner = get(obs, *positional, **kwargs)
            norms = torch.stack([torch.stack([s.square().mean((0, 2)) for s in expert.states]).sum(0)
                                 for expert in experts], -1)
            proposed = [expert.get_action(obs, is_deterministic=True) for expert in experts]
            mu = torch.where(source3[:, None], raw_mu[1], raw_mu[0])
            label = torch.where(source3[:, None], proposed[1], proposed[0])
            assert torch.isfinite(mu).all() and torch.allclose(label, mu.clamp(-1, 1), atol=1e-6)
            behavior = label if args.mode == 'handover' and len(rows) >= handover else learner
            raw_target = env.init_targets[:, :20] + label * .04
            raw_target[:, 16:] = env.prev_targets[:, 16:20] + label[:, 16:] * .025
            values = dict(obs=obs, previous_action=env.actions, previous_target=env.prev_targets[:, :20],
                          initial_target=env.init_targets[:, :20], active_before=env.eval_active_mask,
                          mu=mu, executed_action=label, behavior_action=behavior,
                          target_unclipped=raw_target, target_clipped=env.actions_to_targets(label),
                          expert_state_norm_before=norms)
            rows.append({k: v.detach().cpu().numpy().copy() for k, v in values.items()})
            return behavior

        def env_step(*positional, **kwargs):
            result = step(*positional, **kwargs)
            rows[-1]['done'] = result[2].detach().cpu().numpy().copy()
            ids = result[2].nonzero(as_tuple=False).squeeze(-1)
            for expert in experts:
                for state in expert.states:
                    state[:, ids, :] = 0
            return result

        player.get_action, player.env_step = action, env_step
        return env, player

    audit.make_player = make
    sys.argv = ['evaluate', '--checkpoint', str(args.checkpoint), '--initial-states', str(args.states),
                '--output', str(args.output), '--stage-seconds', str(args.seconds), '--protocol', 'S',
                '--task', 'wuji_multigrasp', '--hand', 'wuji_paper_official_actuator',
                '--object', 'knife_wuji_bridge3_20260922', '--seed', str(args.seed)]
    try:
        audit.main()
    finally:
        audit.make_player = original_make
    assert len(rows) == 600, 'Preserve incomplete diagnostic; do not train from an unlabelled short run'
    sequence = {k: np.stack([r[k] for r in rows]) for k in rows[0]}
    assert not sequence['expert_state_norm_before'][0].any()
    reset = sequence['done'][:-1].astype(bool)
    assert not sequence['expert_state_norm_before'][1:][reset].any()
    live = sequence['active_before'][1:].astype(bool) & ~reset
    assert np.allclose(sequence['previous_action'][1:][live], sequence['behavior_action'][:-1][live], atol=1e-6)
    # Replay the entire recorded history from zero RNN states, including resets.
    maximum = 0.
    for index, expert in enumerate(experts):
        init_player_rnn_for_batch(expert, 128)
        selected = slice(0, 96) if index == 0 else slice(96, 128)
        for t in range(600):
            obs = torch.as_tensor(sequence['obs'][t], device=expert.device)
            expert.get_action(obs, is_deterministic=True)
            actual = raw_mu[index][selected].cpu().numpy()
            maximum = max(maximum, float(np.max(np.abs(actual - sequence['mu'][t, selected]))))
            ids = np.flatnonzero(sequence['done'][t])
            for state in expert.states:
                state[:, ids, :] = 0
    assert maximum < 1e-5, 'Expert labels do not replay from the recorded actual history'
    report = json.loads((args.output / 'report.json').read_text())
    with np.load(args.output / 'trace.npz') as z:
        trace = {k: z[k] for k in z.files}
    assert np.allclose(trace['action'][trace['active']], sequence['behavior_action'][trace['active']], atol=1e-6)
    report.update(control_mode='same_unified_learner' if args.mode == 'behavior' else 'scripted_responsible_expert_handover',
                  scope=__doc__, handover_step=handover if args.mode == 'handover' else None,
                  expert_checkpoint_sha256=[sha(p) for p in expert_paths], teacher_replay_max_mu_error=maximum)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    for source in range(4):
        dest = args.output / f'source{source}'
        dest.mkdir()
        ids = slice(source * n, (source + 1) * n)
        data = {k: v[:, ids] for k, v in sequence.items()}
        part = {k: v[:, ids] for k, v in trace.items()}
        np.savez_compressed(dest / 'sequences.npz', **data)
        np.savez_compressed(dest / 'trace.npz', **part)
        scored = score_timed_trace(part, args.seconds * 30, 9, 600)
        scored.update(protocol=report['protocol'], source=source, mode=args.mode,
                      scope='Training-state collection or scripted handover; not development/final capability')
        (dest / 'report.json').write_text(json.dumps(scored, indent=2) + '\n')
        info = dict(**metadata, checkpoint_sha256=sha(expert_paths[int(source == 3)]),
                    behavior_checkpoint_sha256=sha(args.checkpoint), source=source, mode=args.mode,
                    steps=600, num_envs=32, sequence_sha256=sha(dest / 'sequences.npz'),
                    action_mode='executed_action is clipped expert label; behavior_action is actual applied action',
                    expert_history='Own normalizer/RNN from same reset; actual observations and previous behavior actions; done resets',
                    teacher_replay_max_mu_error=maximum, collector_sha256=sha(__file__))
        (dest / 'interface.json').write_text(json.dumps(info, indent=2) + '\n')
    (args.output / 'completed.json').write_text(json.dumps(dict(mode=args.mode, steps=600,
        source_trials=32, teacher_replay_max_mu_error=maximum, train_allowed=args.mode == 'behavior')) + '\n')


if __name__ == '__main__':
    main()
