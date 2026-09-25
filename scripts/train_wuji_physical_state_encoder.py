"""Supervised state estimation, then student-only closed-loop data aggregation.

Frozen teacher actor/encoder/normalizers. Teacher-driven warmup is explicitly
separate and never scored as student success. Reset physics and recurrent
memory at handoff. This is a Wuji transfer experiment, not paper latent MSE.
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
from scripts.check_wuji_student_actor_runtime import TEACHER, STUDENT, STUDENT_SHA
from scripts.monitor_wuji_checkpoints import atomic_json, now
from scripts.wuji_physical_state_encoder import history_input, make_encoder, encode_target, decode_prediction, SCALES

ROOT = Path(__file__).resolve().parents[1]
TEACHER_SHA = '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--num-envs', type=int, default=2048)
    p.add_argument('--warmup-updates', type=int, default=100)
    p.add_argument('--student-updates', type=int, default=500)
    p.add_argument('--lr', type=float, default=2e-4)
    p.add_argument('--seed', type=int, default=20261071)
    p.add_argument('--runtime-only', action='store_true')
    args = p.parse_args()
    assert args.num_envs > 0 and args.warmup_updates > 0 and args.student_updates > 0 and args.lr >= 0
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    assert hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest() == TEACHER_SHA
    assert hashlib.sha256((ROOT/STUDENT).read_bytes()).hexdigest() == STUDENT_SHA
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
    # Reuse architecture specification only; no trained student weight is read.
    artifact = torch.load(ROOT/STUDENT, map_location='cpu')
    encoder, spec = make_encoder(artifact['distill_meta']['student_encoder_spec'])
    encoder.to(player.device).eval()
    initial_encoder = tensor_digest(encoder.state_dict())
    optimizer = torch.optim.Adam(encoder.parameters(), lr=args.lr)
    props = env.object_cfg['default_props']
    properties = torch.tensor(list(props['mass']) + [props['friction'], props['dof_damping'], props.get('dof_stiffness', 0.)], device=player.device).reshape(1, 5)
    control = dict(enabled=False)
    checks = dict(teacher_physics_transitions=0, student_physics_transitions=0,
                  presim_action_checks=0, privileged_invariance=0, kinematic_max_m=0., kinematic_max_quaternion=0.,
                  latest_history_matches=0, shifted_history_matches=0, changed_history_rows=0)
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
    state = dict(status='running', started=now(), checks=checks, arguments={**vars(args), 'output':str(args.output)},
                 teacher_sha256=TEACHER_SHA, initial_encoder_sha256=initial_encoder, spec=spec,
                 observation='50x40 measured joints/actions +55 initial acquisition-frame fields',
                 loss='mean SmoothL1 beta1 on8 physical residuals; scales [1mm,1mm,1mm,.02rad,.02rad,.02rad,.5mm,.01m/s]',
                 nominal_properties=properties[0].tolist(), scope=__doc__)
    atomic_json(args.output/'status.json', state)
    def save(phase, update):
        path = args.output/'checkpoints'/('%s_%06d.pth'%(phase, update))
        path.parent.mkdir(exist_ok=True)
        assert not path.exists()
        payload = dict(state_encoder=encoder.state_dict(), encoder_spec=spec, scales=SCALES,
                       optimizer=optimizer.state_dict(), phase=phase, update=update,
                       teacher_sha256=TEACHER_SHA, nominal_properties=properties[0].tolist(), protocol=state['observation'])
        torch.save(payload, path.with_suffix('.tmp'))
        os.replace(path.with_suffix('.tmp'), path)
        atomic_json(path.with_suffix('.json'), dict(phase=phase, update=update,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), committed=now(), checks=checks.copy()))
    try:
        for phase, updates in [('warmup', args.warmup_updates), ('student', args.student_updates)]:
            observations = player.env_reset(player.env)
            for memory in player.states:
                memory.zero_()
            assert all(torch.count_nonzero(m) == 0 for m in player.states)
            # Handoff resets histories, physics and all teacher-fed recurrent state.
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
                    checks[('teacher' if phase == 'warmup' else 'student')+'_physics_transitions'] += env.num_envs
                x = torch.cat(histories)
                y = torch.cat(targets)
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
                assert all(torch.isfinite(v).all() for v in encoder.state_dict().values())
                error = torch.cat(errors)*x.new_tensor(SCALES)
                metrics = dict(phase=phase, update=update, loss=loss_total, grad_norm=float(grad_norm),
                    rmse_physical=error.square().mean(0).sqrt().cpu().tolist(),
                    teacher_physics_transitions=checks['teacher_physics_transitions'], student_physics_transitions=checks['student_physics_transitions'])
                with (args.output/'metrics.jsonl').open('a') as file:
                    file.write(json.dumps(metrics)+'\n')
                state.update(phase=phase, updates_completed=update, heartbeat=now(), latest=metrics)
                atomic_json(args.output/'status.json', state)
                if update in (1, updates) or update % 25 == 0:
                    save(phase, update)
                print(json.dumps(metrics), flush=True)
        assert tensor_digest(model.state_dict()) == before
        final_encoder = tensor_digest(encoder.state_dict())
        assert (final_encoder == initial_encoder) == (args.lr == 0)
        expected = (args.warmup_updates+args.student_updates)*16*env.num_envs
        assert checks['presim_action_checks'] == expected
        if args.runtime_only:
            assert checks['privileged_invariance'] == args.student_updates*16*env.num_envs
            assert checks['shifted_history_matches'] > 0 and checks['changed_history_rows'] > 0
        assert checks['latest_history_matches'] == expected
        state.update(status='completed', finished=now())
        atomic_json(args.output/'status.json', state)
        atomic_json(args.output/'report.json', dict(status='passed', teacher_unchanged=True,
            encoder_changed=final_encoder!=initial_encoder, final_encoder_sha256=final_encoder,
            teacher_model_tensor_sha256=before, checks=checks, no_success_claim=True))
    except BaseException as error:
        state.update(status='failed', error=repr(error), finished=now())
        atomic_json(args.output/'status.json', state)
        raise
    finally:
        handle.remove()


if __name__ == '__main__':
    main()
