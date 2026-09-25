"""Continue an offline state fit with student-only physics and a matched teacher-replay control.

Teacher history is supervised training data only. Both arms have the same
initial weights, fresh Adam, current-data batch and total supervised sample
budget. Runtime/preflight states and weights never seed the formal run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
import numpy as np
import torch
from torch import nn
from omegaconf import OmegaConf
from isaacgymenvs.distill import reset_done_rnn_states
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.monitor_wuji_checkpoints import atomic_json, now
from scripts.wuji_physical_state_encoder import history_input, make_encoder, encode_target, decode_prediction, SCALES

ROOT = Path(__file__).resolve().parents[1]
TEACHER_SHA = '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--num-envs', type=int, default=1024)
    p.add_argument('--initial', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--arm', choices=['current', 'teacher_replay'], required=True)
    p.add_argument('--updates', type=int, default=500)
    p.add_argument('--lr', type=float, default=2e-5)
    p.add_argument('--seed', type=int, default=20261073)
    p.add_argument('--runtime-only', action='store_true')
    args = p.parse_args()
    assert args.num_envs > 0 and args.updates > 0 and args.lr >= 0
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    assert hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest() == TEACHER_SHA
    metadata = json.loads(args.initial.with_suffix('.json').read_text())
    assert hashlib.sha256(args.initial.read_bytes()).hexdigest() == metadata['sha256']
    artifact = torch.load(args.initial, map_location='cpu')
    assert artifact['phase'] == 'offline_teacher_fit' and artifact['update'] == 1000
    assert artifact['teacher_sha256'] == TEACHER_SHA
    assert np.allclose(artifact['output_scales'], SCALES, rtol=1e-6, atol=1e-10)
    manifest = json.loads(args.dataset.with_name('dataset-manifest.json').read_text())
    assert manifest['status'] == 'passed' and manifest['teacher_unchanged']
    assert manifest['source_teacher_sha256'] == TEACHER_SHA
    assert hashlib.sha256(args.dataset.read_bytes()).hexdigest() == manifest['dataset_sha256']
    cfg = configuration('wuji_acquisition_bridge3_hemisphere', args.num_envs,
        ['hand=wuji_paper_official_actuator', 'object=knife_wuji_bridge3_20260922',
         'task.env.proprioHistoryLen=50', '+task.env.enableStudentEncoderObs=True'], train='wujiAcquisitionSAPG', seed=args.seed)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, ROOT/TEACHER)
    assert not env.eval_mode and env.student_encoder_obs_enabled and env.joint_noise == 0
    model = player.model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    before = tensor_digest(model.state_dict())
    # Both arms start from exactly the same completed fixed-data fit.
    encoder, spec = make_encoder(artifact['encoder_spec'])
    encoder.load_state_dict(artifact['state_encoder'])
    encoder.to(player.device).eval()
    initial_encoder = tensor_digest(encoder.state_dict())
    optimizer = torch.optim.Adam(encoder.parameters(), lr=args.lr)
    with np.load(args.dataset) as z:
        selected = z['active'] & z['train_rows'][None, :]
        assert int(selected.sum()) == 9000
        replay_x = torch.from_numpy(z['history'][selected].copy()).to(player.device)
        replay_y = torch.from_numpy(z['target'][selected].copy()).to(player.device)
        replay_y = replay_y / replay_y.new_tensor(SCALES)
    assert replay_x.shape == (9000, 2055) and replay_y.shape == (9000, 8)
    replay_digest = tensor_digest(dict(x=replay_x, y=replay_y))
    # Sampling is isolated from all simulator/actor random streams.
    batch_rng = torch.Generator(device='cpu').manual_seed(args.seed+100000)
    supervised_counts = dict(current=0, teacher=0)
    optimizer_steps = 0
    props = env.object_cfg['default_props']
    properties = torch.tensor(list(props['mass']) + [props['friction'], props['dof_damping'], props.get('dof_stiffness', 0.)], device=player.device).reshape(1, 5)
    control = dict(enabled=False)
    checks = dict(teacher_physics_transitions=0, student_physics_transitions=0,
                  presim_action_checks=0, privileged_invariance=0, kinematic_max_m=0., kinematic_max_quaternion=0.,
                  latest_history_matches=0, shifted_history_matches=0, changed_history_rows=0, reset_rows=0)
    def hook(module, inputs):
        if control['enabled']:
            return (control['normalized_prediction'],)
    handle = model.a2c_network.priv_encoder.register_forward_pre_hook(hook)
    pre = env.pre_physics_step
    def pre_step(action):
        pre(action)
        assert torch.equal(env.actions, control['action'])
        checks['presim_action_checks'] += env.num_envs
    env.pre_physics_step = pre_step
    state = dict(status='running', started=now(), checks=checks, arguments={**vars(args), 'output':str(args.output), 'initial':str(args.initial), 'dataset':str(args.dataset)},
                 teacher_sha256=TEACHER_SHA, initial_encoder_sha256=initial_encoder, spec=spec,
                 observation='50x40 measured joints/actions +55 initial acquisition-frame fields',
                 loss='mean SmoothL1 beta1 on8 physical residuals; scales [1mm,1mm,1mm,.02rad,.02rad,.02rad,.5mm,.01m/s]',
                 nominal_properties=properties[0].tolist(), scope=__doc__,
                 initial_artifact_sha256=metadata['sha256'], dataset_sha256=manifest['dataset_sha256'],
                 replay_tensor_sha256=replay_digest, supervised_counts=supervised_counts,
                 sampling='4096 first current samples; 4096 second current or fixed teacher samples; replacement; equal total8192 per update; private RNG', 
                 fresh_optimizer=True, optimizer_steps=0)
    atomic_json(args.output/'status.json', state)
    def save(phase, update):
        path = args.output/'checkpoints'/('%s_%06d.pth'%(phase, update))
        path.parent.mkdir(exist_ok=True)
        assert not path.exists()
        payload = dict(state_encoder=encoder.state_dict(), encoder_spec=spec, scales=SCALES,
                       optimizer=optimizer.state_dict(), phase=phase, update=update,
                       teacher_sha256=TEACHER_SHA, nominal_properties=properties[0].tolist(), protocol=state['observation'], provenance=dict(arm=args.arm, initial_sha256=metadata['sha256'],
                       dataset_sha256=manifest['dataset_sha256'], supervised_counts=supervised_counts.copy(),
                       teacher_physics_transitions=0, student_physics_transitions=checks['student_physics_transitions']))
        torch.save(payload, path.with_suffix('.tmp'))
        os.replace(path.with_suffix('.tmp'), path)
        atomic_json(path.with_suffix('.json'), dict(phase=phase, update=update,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), committed=now(), checks=checks.copy()))
    try:
        for phase, updates in [('student', args.updates)]:
            observations = player.env_reset(player.env)
            for memory in player.states:
                memory.zero_()
            assert all(torch.count_nonzero(m) == 0 for m in player.states)
            state['initial_observation_tensor_sha256'] = tensor_digest(dict(observation=observations[:, :132]))
            # Fresh reset and zero actor/critic memory; no teacher rollout prefix.
            save(phase, 0)
            for update in range(1, updates+1):
                histories, targets, errors = [], [], []
                for t in range(16):
                    history = history_input(env.proprioception_buf, observations)
                    assert history.shape == (env.num_envs, 2055) and torch.isfinite(history).all()
                    assert torch.equal(env.proprioception_buf[:, -1], observations[:, 55:95])
                    checks['latest_history_matches'] += env.num_envs
                    previous_history = env.proprioception_buf.clone() if args.runtime_only else None
                    target = encode_target(observations[:, :55], observations[:, 111:132])
                    with torch.no_grad():
                        predicted = encoder(history)
                        physical = decode_prediction(observations[:, :55], predicted, properties)
                        if args.runtime_only:
                            recovered = decode_prediction(observations[:, :55], target, observations[:, 125:130])
                            position_error = float((recovered[:, [0,1,2,7,8,9]] - observations[:, [111,112,113,118,119,120]]).abs().max())
                            quaternion_error = float((recovered[:, [3,4,5,6,10,11,12,13]] - observations[:, [114,115,116,117,121,122,123,124]]).abs().max())
                            checks['kinematic_max_m'] = max(checks['kinematic_max_m'], position_error)
                            checks['kinematic_max_quaternion'] = max(checks['kinematic_max_quaternion'], quaternion_error)
                            assert position_error < 5e-5 and quaternion_error < 5e-4
                        modified = observations.clone()
                        modified[:, 111:132] = physical
                        control['normalized_prediction'] = model.norm_obs(player._preproc_obs(modified))[:, 111:132]
                        control['enabled'] = phase == 'student'
                        incoming = [m.clone() for m in player.states]
                        action = player.get_action(observations, is_deterministic=True)
                        outgoing = [m.clone() for m in player.states]
                        if args.runtime_only and phase == 'student':
                            changed = observations.clone()
                            changed[:, 111:137] += 7.
                            assert torch.equal(history_input(env.proprioception_buf, changed), history)
                            assert torch.equal(encoder(history_input(env.proprioception_buf, changed)), predicted)
                            player.states = incoming
                            other = player.get_action(changed, is_deterministic=True)
                            assert torch.equal(other, action)
                            assert all(torch.equal(a, b) for a, b in zip(outgoing[:2], player.states[:2]))
                            player.states = outgoing
                            checks['privileged_invariance'] += env.num_envs
                    histories.append(history.detach())
                    targets.append(target.detach())
                    errors.append((predicted-target).detach())
                    control['action'] = action.clone()
                    observations, _, done, _ = player.env_step(player.env, action)
                    if args.runtime_only:
                        continuing = ~done.reshape(-1).bool()
                        assert torch.equal(env.proprioception_buf[continuing, :-1], previous_history[continuing, 1:])
                        checks['shifted_history_matches'] += int(continuing.sum())
                        checks['changed_history_rows'] += int((env.proprioception_buf != previous_history).reshape(env.num_envs, -1).any(-1).sum())
                    reset_done_rnn_states(player, done)
                    checks['reset_rows'] += int(done.reshape(-1).bool().sum())
                    checks[('teacher' if phase == 'warmup' else 'student')+'_physics_transitions'] += env.num_envs
                current_x = torch.cat(histories)
                current_y = torch.cat(targets)
                # Consume all three index streams in both arms; changing the
                # replay arm cannot perturb the simulator or first-current draw.
                first_index = torch.randint(len(current_x), (4096,), generator=batch_rng).to(player.device)
                second_index = torch.randint(len(current_x), (4096,), generator=batch_rng).to(player.device)
                teacher_index = torch.randint(len(replay_x), (4096,), generator=batch_rng).to(player.device)
                second_x, second_y = ((current_x[second_index], current_y[second_index]) if args.arm=='current'
                                      else (replay_x[teacher_index], replay_y[teacher_index]))
                x = torch.cat([current_x[first_index], second_x])
                y = torch.cat([current_y[first_index], second_y])
                assert x.shape == (8192, 2055) and y.shape == (8192, 8)
                if args.runtime_only:
                    assert torch.equal(x[:4096], current_x[first_index])
                    assert torch.equal(y[:4096], current_y[first_index])
                    assert torch.equal(x[4096:], second_x) and torch.equal(y[4096:], second_y)
                supervised_counts['current'] += 8192 if args.arm=='current' else 4096
                supervised_counts['teacher'] += 0 if args.arm=='current' else 4096
                optimizer.zero_grad(set_to_none=True)
                loss_total = 0.
                for start in range(0, len(x), 2048):
                    prediction = encoder(x[start:start+2048])
                    loss = nn.functional.smooth_l1_loss(prediction, y[start:start+2048], reduction='sum') / y.numel()
                    assert torch.isfinite(loss)
                    loss.backward()
                    loss_total += float(loss.detach())
                grad_norm = torch.nn.utils.clip_grad_norm_(encoder.parameters(), 1., error_if_nonfinite=True)
                optimizer.step()
                optimizer_steps += 1
                assert all(torch.isfinite(v).all() for v in encoder.state_dict().values())
                error = torch.cat(errors)*x.new_tensor(SCALES)
                metrics = dict(phase=phase, update=update, loss=loss_total, grad_norm=float(grad_norm),
                    rmse_physical=error.square().mean(0).sqrt().cpu().tolist(),
                    teacher_physics_transitions=checks['teacher_physics_transitions'], student_physics_transitions=checks['student_physics_transitions'])
                with (args.output/'metrics.jsonl').open('a') as file:
                    file.write(json.dumps(metrics)+'\n')
                state.update(phase=phase, updates_completed=update, heartbeat=now(), latest=metrics, optimizer_steps=optimizer_steps)
                atomic_json(args.output/'status.json', state)
                if update in (1, updates) or update % 25 == 0:
                    save(phase, update)
                print(json.dumps(metrics), flush=True)
        assert tensor_digest(model.state_dict()) == before
        final_encoder = tensor_digest(encoder.state_dict())
        assert (final_encoder == initial_encoder) == (args.lr == 0)
        expected = args.updates*16*env.num_envs
        assert checks['presim_action_checks'] == expected
        if args.runtime_only:
            assert checks['privileged_invariance'] == args.updates*16*env.num_envs
            assert checks['shifted_history_matches'] > 0 and checks['changed_history_rows'] > 0
            assert checks['reset_rows'] > 0
        assert checks['latest_history_matches'] == expected
        assert checks['teacher_physics_transitions'] == 0
        assert checks['student_physics_transitions'] == expected
        assert optimizer_steps == args.updates
        assert sum(supervised_counts.values()) == 8192 * args.updates
        assert supervised_counts['teacher'] == (4096 * args.updates if args.arm=='teacher_replay' else 0)
        assert tensor_digest(dict(x=replay_x, y=replay_y)) == replay_digest
        state.update(status='completed', finished=now())
        atomic_json(args.output/'status.json', state)
        atomic_json(args.output/'report.json', dict(status='passed', teacher_unchanged=True,
            encoder_changed=final_encoder!=initial_encoder, final_encoder_sha256=final_encoder,
            teacher_model_tensor_sha256=before, checks=checks, supervised_counts=supervised_counts,
            initial_encoder_sha256=initial_encoder, initial_artifact_sha256=metadata['sha256'],
            optimizer_steps=optimizer_steps, no_success_claim=True))
    except BaseException as error:
        state.update(status='failed', error=repr(error), finished=now())
        atomic_json(args.output/'status.json', state)
        raise
    finally:
        handle.remove()


if __name__ == '__main__':
    main()
