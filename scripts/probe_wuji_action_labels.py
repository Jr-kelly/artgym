"""Read-only teacher-label diagnostics on physical student-driven rollouts.

The teacher keeps its own recurrent history. Neither its labels nor its hidden
states reach the student. The existing fixed-clock physics/scorer is reused.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from scripts import wuji_goal_common  # Isaac Gym before torch.
import numpy as np
import torch
from rl_games.algos_torch import models
from rl_games.algos_torch.players import rescale_actions
from isaacgymenvs.learning.a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder
from isaacgymenvs.distill import reset_done_rnn_states
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER

ROOT = Path(__file__).resolve().parents[1]


def states_copy(states):
    return [x.detach().clone() for x in states]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, choices=[2, 5], required=True)
    parser.add_argument('--runtime-check', action='store_true')
    args = parser.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    assert hashlib.sha256((ROOT / TEACHER).read_bytes()).hexdigest() == '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
    original_make = wuji_goal_common.make_player
    rows, refs = [], {}
    checks = dict(actual_student_actions=0, student_reference_parity=0,
                  teacher_reference_parity=0, label_no_student_rnn_change=0, label_no_rng_change=0)

    def make_player(cfg, checkpoint):
        env, player = original_make(cfg, checkpoint)
        model = player.model.eval()
        device = player.device
        before = tensor_digest(model.state_dict())
        encoder_before = tensor_digest(env.fixed_student_encoder.state_dict())
        # These are copies, not the live student's modules/normalization.
        teacher_network = copy.deepcopy(model.a2c_network)
        teacher_network.__class__ = A2CSAPGPrivBuilder.Network
        teacher = models.ModelA2CContinuousLogStd.Network(teacher_network,
            obs_shape=(138,), normalize_value=True, normalize_input=True,
            value_size=1, extra_info_start_idx=137).to(device)
        payload = torch.load(ROOT / TEACHER, map_location=device)
        teacher.load_state_dict((payload[0] if 0 in payload else payload)['model'])
        teacher.eval()
        teacher_player = copy.copy(player)
        teacher_player.model = teacher
        teacher_player.obs_shape = (138,)
        teacher_player.states = states_copy(player.states)
        teacher_before = tensor_digest(teacher.state_dict())
        refs.update(model=model, teacher=teacher, encoder=env.fixed_student_encoder,
                    before=before, teacher_before=teacher_before, encoder_before=encoder_before)
        original_action = player.get_action
        original_step = player.env_step
        pre_physics = env.pre_physics_step
        expected_action = []

        def pre_step(action):
            pre_physics(action)
            assert len(expected_action) == 1
            assert torch.equal(env.actions, expected_action[0])
            checks['actual_student_actions'] += env.num_envs

        def step(*pargs, **kwargs):
            result = original_step(*pargs, **kwargs)
            reset_done_rnn_states(teacher_player, result[2])
            return result

        def observed(obs, is_deterministic=False, **kwargs):
            assert is_deterministic
            incoming = states_copy(player.states)
            capture = {}
            def hook(module, inputs, result):
                capture['mu'] = result['mus'].detach().clone()
            handle = model.register_forward_hook(hook)
            try:
                action = original_action(obs, is_deterministic=True, **kwargs)
            finally:
                handle.remove()
            mean = capture['mu']
            outgoing = states_copy(player.states)
            assert torch.equal(action, rescale_actions(player.actions_low, player.actions_high, mean.clamp(-1, 1)))
            cpu_rng, cuda_rng = torch.get_rng_state(), torch.cuda.get_rng_state(device)
            legacy = torch.cat([obs[:, :137], obs[:, 153:154]], dim=1)
            with torch.no_grad(), torch.random.fork_rng(devices=[torch.device(device).index or 0]):
                teacher_incoming = states_copy(teacher_player.states)
                result = teacher(dict(is_train=False, prev_actions=None,
                    obs=teacher_player._preproc_obs(legacy), rnn_states=teacher_player.states))
                label = result['mus'].detach().clone()
                label_action = rescale_actions(player.actions_low, player.actions_high, label.clamp(-1, 1))
                teacher_player.states = states_copy(result['rnn_states'])
                if args.runtime_check:
                    saved_teacher = states_copy(teacher_player.states)
                    teacher_player.states = teacher_incoming
                    reference = teacher_player.get_action(legacy, is_deterministic=True)
                    assert torch.equal(reference, label_action)
                    assert all(torch.equal(a, b) for a, b in zip(teacher_player.states, saved_teacher))
                    checks['teacher_reference_parity'] += env.num_envs
                    player.states = states_copy(incoming)
                    reference = original_action(obs, is_deterministic=True, **kwargs)
                    assert torch.equal(reference, action)
                    assert all(torch.equal(a, b) for a, b in zip(player.states, outgoing))
                    player.states = outgoing
                    checks['student_reference_parity'] += env.num_envs
                # Report the existing control map before actuator smoothing.
                target = env.actions_to_targets(action)
                label_target = env.actions_to_targets(label_action)
            assert torch.equal(torch.get_rng_state(), cpu_rng)
            assert torch.equal(torch.cuda.get_rng_state(device), cuda_rng)
            assert all(torch.equal(a, b) for a, b in zip(player.states, outgoing))
            checks['label_no_student_rnn_change'] += env.num_envs
            checks['label_no_rng_change'] += env.num_envs
            expected_action[:] = [action.detach().clone()]
            row = dict(active=env.eval_active_mask, student_mu=mean, teacher_mu=label,
                student_action=action, teacher_action=label_action, student_mapped_target=target,
                teacher_mapped_target=label_target, measured_q=env.hand_dof_pos,
                previous_target=env.prev_targets[:, :20], goal=env.goal_obj_dof_pos[:, 0],
                slider=env.obj_dof_pos[:, 0])
            rows.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})
            return action

        player.get_action = observed
        player.env_step = step
        env.pre_physics_step = pre_step
        return env, player

    wuji_goal_common.make_player = make_player
    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], '--checkpoint', str(args.checkpoint), '--output', str(args.output),
            '--task', 'wuji_fixed_student_actor', '--hand', 'wuji_paper_official_actuator',
            '--object', 'knife_wuji_bridge3_20260922', '--stage-seconds', str(args.seconds),
            '--initial-states', str(ROOT / 'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
            '--seed', '20261060']
        if args.runtime_check:
            sys.argv += ['--initial-state-rows', '0', '100', '200']
        from scripts.audit_wuji_actor_imitation import main as audit
        audit()
    finally:
        sys.argv = old_argv
        wuji_goal_common.make_player = original_make
    assert tensor_digest(refs['model'].state_dict()) == refs['before']
    assert tensor_digest(refs['teacher'].state_dict()) == refs['teacher_before']
    assert tensor_digest(refs['encoder'].state_dict()) == refs['encoder_before']
    assert len(rows) == 600
    count = 3 if args.runtime_check else 332
    assert checks['actual_student_actions'] == checks['label_no_student_rnn_change'] == checks['label_no_rng_change'] == 600 * count
    if args.runtime_check:
        assert checks['student_reference_parity'] == checks['teacher_reference_parity'] == 1800
    trace = {k:np.stack([r[k] for r in rows]) for k in rows[0]}
    np.savez_compressed(args.output / 'action-label-trace.npz', **trace)
    report = dict(status='passed', source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(), runtime_check=args.runtime_check,
        teacher_unchanged=True, student_unchanged=True, encoder_unchanged=True, checks=checks,
        teacher_memory='separate recurrent history of the actual student-induced states',
        note='Read-only diagnostic. Only student actions reach physics. Same development states and scorer; rerun is not independent success evidence. Control-map targets are before actuator smoothing.')
    (args.output / 'label-probe-report.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'label-probe-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
