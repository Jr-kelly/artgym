"""Measure command transport delay for a frozen learned teacher.

Delay applies to emitted absolute hand targets, after the unchanged policy action
mapping. The policy retains its own emitted action/target history. Observations
have no added delay in this experiment. Knife targets, forces and rewards are
unchanged. This is sensitivity analysis, not a calibrated hardware model.
Optional force instrumentation is disabled by default: this installed simulator
returned zero sensor readings in a preserved failed probe, so no force claim is
made for the normal delay series.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from scripts import wuji_goal_common
from isaacgym import gymtorch
from isaacgymenvs.tasks.artmanip import ArtManip
import numpy as np
import torch
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--initial-states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--delay-steps', type=int, choices=[0, 1, 2], required=True)
    parser.add_argument('--stage-seconds', type=int, choices=[2, 5], required=True)
    parser.add_argument('--seed', type=int, default=20261039)
    parser.add_argument('--record-force', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output / 'report.json').exists()
    root = Path(__file__).resolve().parents[1]
    xml_path = root / 'runs/wuji-goal/research/wuji-official/wuji-mjlab/src/wuji_mjlab/assets/robots/wuji_hand/mjcf/right_mjlab.xml'
    xml = ET.parse(xml_path)
    official = {p.get('joint'): p for p in xml.findall('.//actuator/position')}
    digit = dict(index=2, middle=3, pinky=5, ring=4, thumb=1)
    original_make = wuji_goal_common.make_player
    trace, metadata, models = [], {}, []

    def make_player(cfg, checkpoint):
        # PhysX force sensors must exist before prepare_sim allocates tensors.
        original_create = ArtManip._create_envs

        def create_with_sensors(env, *args, **kwargs):
            original_create(env, *args, **kwargs)
            for handle in env.envs:
                actor = env.gym.find_actor_handle(handle, 'hand')
                env.gym.enable_actor_dof_force_sensors(handle, actor)

        if args.record_force:
            ArtManip._create_envs = create_with_sensors
        try:
            env, player = original_make(cfg, checkpoint)
        finally:
            ArtManip._create_envs = original_create
        models.append(player.model)
        metadata['model_before'] = tensor_digest(player.model.state_dict())
        assert not env.randomize and not cfg.object.randomization.randomize
        assert float(cfg.task.env.actionsMovingAverage) == 1.
        hand = env.gym.find_actor_handle(env.envs[0], 'hand')
        names = env.gym.get_actor_dof_names(env.envs[0], hand)
        assert len(names) == 20
        expected = []
        mapping = []
        for name in names:
            components = name.split('_')
            label = 'right_finger%d_joint%s' % (digit[components[2]], components[3][-1])
            value = official[label]
            limits = np.asarray(value.get('forcerange').split(), dtype=float)
            assert np.isclose(limits[0], -limits[1])
            expected.append(limits[1])
            mapping.append(dict(artbot=name, official=label, effort_nm=float(limits[1])))
        for handle in env.envs:
            actor = env.gym.find_actor_handle(handle, 'hand')
            props = env.gym.get_actor_dof_properties(handle, actor)
            assert np.allclose(props['effort'], expected, rtol=1e-6, atol=1e-7)
            for key in ['stiffness', 'damping', 'armature']:
                assert np.allclose(props[key], cfg.hand.dof_props[key], rtol=1e-6, atol=1e-7)
        force_tensor = None
        if args.record_force:
            force_tensor = gymtorch.wrap_tensor(env.gym.acquire_dof_force_tensor(env.sim)).view(env.num_envs, -1)
            assert force_tensor.shape[1] == 21
        original_pre = env.pre_physics_step
        original_reward = env.compute_reward
        history, commands = deque(), []
        physical = [None]

        def pre(actions):
            if not commands:
                history.extend(env.prev_targets.clone() for _ in range(args.delay_steps))
                metadata['initial_hold_targets'] = env.prev_targets[:, :20].detach().cpu().numpy().tolist()
            original_pre(actions)
            emitted = env.cur_targets.clone()
            commands.append(emitted[:, :20].detach().cpu().numpy().copy())
            history.append(emitted)
            physical[0] = history.popleft()
            # All control targets, including the passive object slot, are finite.
            assert torch.isfinite(physical[0]).all()
            assert torch.equal(physical[0][:, 20:], env.cur_targets[:, 20:])
            env.gym.set_dof_position_target_tensor(env.sim, gymtorch.unwrap_tensor(physical[0]))
            assert torch.equal(env.cur_targets, emitted)

        def reward(actions):
            active = env.eval_active_mask.clone()
            row = dict(active=active,
                       physical_target=physical[0][:, :20], emitted_target=env.cur_targets[:, :20],
                       q=env.hand_dof_pos, qvel=env.hand_dof_vel)
            if force_tensor is not None:
                env.gym.refresh_dof_force_tensor(env.sim)
                row['sensed_force'] = force_tensor[:, :20]
            trace.append({k: v.detach().cpu().numpy().copy() for k, v in row.items()})
            original_reward(actions)

        env.pre_physics_step = pre
        env.compute_reward = reward
        metadata.update(delay_steps=args.delay_steps, delay_seconds=args.delay_steps * env.dt * env.control_freq_inv,
                        mapping=mapping, actual_effort_matches_official=True, emitted_target_history_preserved=True,
                        state_observation_delay_steps=0, num_envs=env.num_envs)
        return env, player

    wuji_goal_common.make_player = make_player
    from scripts import audit_wuji_timed_commands
    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], '--checkpoint', str(args.checkpoint), '--initial-states', str(args.initial_states),
                    '--output', str(args.output), '--task', 'wuji_acquisition_official_timed2',
                    '--hand', 'wuji_paper_official_actuator', '--object', 'knife_wuji_precision_near01',
                    '--stage-seconds', str(args.stage_seconds), '--seed', str(args.seed)]
        audit_wuji_timed_commands.main()
    finally:
        sys.argv = old_argv
        wuji_goal_common.make_player = original_make
    metadata['model_after'] = tensor_digest(models[0].state_dict())
    assert metadata['model_after'] == metadata['model_before']
    arrays = {k: np.stack([t[k] for t in trace]) for k in trace[0]}
    assert arrays['active'].shape[0] == 600
    delay = args.delay_steps
    actual, emitted = arrays['physical_target'], arrays['emitted_target']
    expected = np.asarray(metadata.pop('initial_hold_targets'), dtype=np.float32)
    if delay:
        assert np.array_equal(actual[:delay], np.repeat(expected[None], delay, axis=0))
        assert np.array_equal(actual[delay:], emitted[:-delay])
    else:
        assert np.array_equal(actual, emitted)
    force_metadata = dict(force_instrumentation_enabled=args.record_force)
    if args.record_force:
        assert np.isfinite(arrays['sensed_force']).all()
        active_force = np.abs(arrays['sensed_force'][arrays['active']])
        assert active_force.max() > 1e-6, 'Force instrumentation returned only zeros'
        limits = np.asarray([v['effort_nm'] for v in metadata['mapping']])
        force_metadata.update(sensed_force_max_abs_nm_per_joint=active_force.max(0).tolist(),
                    sensed_force_abs_quantiles_nm=np.quantile(active_force, [.5, .9, .99, 1.]).tolist(),
                    fraction_sensed_force_above_effort_per_joint=(active_force > limits * 1.01).mean(0).tolist())
    metadata.update(status='completed', scope=__doc__, steps=600, target_delay_verified_exactly=True,
                    sensor_caveat='Isaac Gym DOF force sensors report joint forces; they are not a hardware current/torque calibration.',
                    checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                    initial_states_sha256=hashlib.sha256(args.initial_states.read_bytes()).hexdigest(),
                    official_mjcf_sha256=hashlib.sha256(xml_path.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    metadata.update(force_metadata)
    np.savez_compressed(args.output / 'command_force_trace.npz', **arrays)
    (args.output / 'latency_probe_source.py').write_bytes(Path(__file__).read_bytes())
    (args.output / 'command-force-report.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({k: v for k, v in metadata.items() if k not in ['mapping', 'scope']}), flush=True)


if __name__ == '__main__':
    main()
