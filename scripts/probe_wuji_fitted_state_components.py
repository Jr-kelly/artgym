"""Diagnose fitted-state errors by independently replacing body and slider feedback with current truth.

Hybrid conditions are privileged controller diagnostics, never deployable student
success. All conditions use coherent moving-link reconstruction and frozen weights.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.wuji_physical_state_encoder import history_input, make_encoder, encode_target, decode_prediction, SCALES

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seconds', type=int, choices=[2,5], required=True)
    p.add_argument('--runtime-check', action='store_true')
    p.add_argument('--condition', choices=['estimated','true_body','true_slider','true_both',
        'true_slider_position','true_slider_velocity','zero_slider_velocity'], required=True)
    args = p.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    metadata = json.loads(args.artifact.with_suffix('.json').read_text())
    assert hashlib.sha256(args.artifact.read_bytes()).hexdigest() == metadata['sha256']
    artifact = torch.load(args.artifact, map_location='cpu')
    teacher = ROOT/TEACHER
    assert hashlib.sha256(teacher.read_bytes()).hexdigest() == artifact['teacher_sha256']
    assert artifact['phase'] == 'offline_teacher_fit'
    assert len(artifact['output_scales']) == 8
    original = wuji_goal_common.make_player
    refs = {}
    checks = dict(physics_transitions=0, actor_input_checks=0, same_state_reference=0,
                  latest_history_matches=0, changed_history_rows=0,
                  kinematic_position_max_m=0., kinematic_quaternion_max=0.,
                  reference_action_max=0., reference_actor_rnn_max=0.)
    rows = []
    truth_indices = dict(estimated=[], true_body=list(range(6)), true_slider=[6,7],
        true_both=list(range(8)), true_slider_position=[6], true_slider_velocity=[7],
        zero_slider_velocity=[])[args.condition]
    checks['privileged_invariance'] = 0
    def make_player(cfg, path):
        cfg.task.env.proprioHistoryLen = 50
        OmegaConf.update(cfg, 'task.env.enableStudentEncoderObs', True, force_add=True)
        env, player = original(cfg, path)
        (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
        assert env.student_encoder_obs_enabled and env.joint_noise == 0
        model = player.model.eval()
        with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
            encoder, _ = make_encoder(artifact['encoder_spec'])
            encoder.load_state_dict(artifact['state_encoder'])
            encoder.to(player.device).eval()
        props = torch.tensor(artifact['nominal_properties'], device=player.device).reshape(1,5)
        unit_ratio = torch.tensor(artifact['output_scales'], device=player.device) / torch.tensor(SCALES, device=player.device)
        refs.update(model=model, encoder=encoder, before_model=tensor_digest(model.state_dict()),
                    before_encoder=tensor_digest(encoder.state_dict()))
        actual = player.get_action
        expected = {}
        enabled=[True]
        def hook(module, inputs):
            if enabled[0]:
                assert torch.equal(inputs[0], expected['true_normalized'])
                checks['actor_input_checks'] += env.num_envs
                return (expected['normalized'],)
        refs['hook'] = model.a2c_network.priv_encoder.register_forward_pre_hook(hook)
        pre = env.pre_physics_step
        def pre_step(action):
            pre(action)
            assert torch.equal(env.actions, expected['action'])
            checks['physics_transitions'] += env.num_envs
        env.pre_physics_step = pre_step
        def action(obs, is_deterministic=False, **kwargs):
            assert is_deterministic
            inputs = history_input(env.proprioception_buf, obs)
            assert torch.equal(env.proprioception_buf[:, -1], obs[:, 55:95])
            checks['latest_history_matches'] += env.num_envs
            if 'history' in expected:
                checks['changed_history_rows'] += int((env.proprioception_buf != expected['history']).reshape(env.num_envs, -1).any(-1).sum())
            expected['history'] = env.proprioception_buf.clone()
            with torch.no_grad():
                prediction = encoder(inputs) * unit_ratio
                target = encode_target(obs[:, :55], obs[:,111:132])
                used = prediction.clone()
                if truth_indices:
                    used[:,truth_indices]=target[:,truth_indices]
                if args.condition == 'zero_slider_velocity':
                    used[:,7] = 0.
                physical = decode_prediction(obs[:, :55], used, props)
                truth=obs[:,111:132]
                reconstructed_truth=decode_prediction(obs[:,:55],target,truth[:,14:19])
                active=env.eval_active_mask
                if active.any():
                    position_error=float((reconstructed_truth[active][:,[0,1,2,7,8,9]]-truth[active][:,[0,1,2,7,8,9]]).abs().max())
                    quaternion_error=float((reconstructed_truth[active][:,[3,4,5,6,10,11,12,13]]-truth[active][:,[3,4,5,6,10,11,12,13]]).abs().max())
                    checks['kinematic_position_max_m']=max(checks['kinematic_position_max_m'],position_error)
                    checks['kinematic_quaternion_max']=max(checks['kinematic_quaternion_max'],quaternion_error)
                    assert position_error<5e-5 and quaternion_error<5e-4
                assert torch.isfinite(used).all() and torch.isfinite(physical).all()
                for index in range(8):
                    desired = (torch.zeros_like(used[:,index]) if args.condition=='zero_slider_velocity' and index==7
                               else target[:,index] if index in truth_indices else prediction[:,index])
                    assert torch.equal(used[:,index], desired)
                modified = obs.clone()
                modified[:,111:132] = physical
                assert torch.equal(modified[:,:111],obs[:,:111]) and torch.equal(modified[:,132:],obs[:,132:])
                expected['normalized'] = model.norm_obs(player._preproc_obs(modified))[:,111:132]
                expected['true_normalized'] = model.norm_obs(player._preproc_obs(obs))[:,111:132]
                incoming = [v.clone() for v in player.states]
                result = actual(obs, is_deterministic=True, **kwargs)
                outgoing = [v.clone() for v in player.states]
                if args.runtime_check:
                    player.states = [v.clone() for v in incoming]
                    enabled[0]=False
                    try:
                        reference=actual(modified,is_deterministic=True,**kwargs)
                    finally:
                        enabled[0]=True
                    action_error=float((reference-result).abs().max())
                    rnn_error=max(float((a-b).abs().max()) for a,b in zip(player.states[:2],outgoing[:2]))
                    checks['reference_action_max']=max(checks['reference_action_max'],action_error)
                    checks['reference_actor_rnn_max']=max(checks['reference_actor_rnn_max'],rnn_error)
                    assert action_error==0 and rnn_error==0
                    player.states=outgoing
                    checks['same_state_reference']+=env.num_envs
                    if not truth_indices:
                        changed = obs.clone(); changed[:,111:137] += 7.
                        assert torch.equal(history_input(env.proprioception_buf, changed), inputs)
                        assert torch.equal(encoder(history_input(env.proprioception_buf, changed))*unit_ratio, prediction)
                        saved_true = expected['true_normalized']
                        expected['true_normalized'] = model.norm_obs(player._preproc_obs(changed))[:,111:132]
                        player.states = [v.clone() for v in incoming]
                        try:
                            other = actual(changed, is_deterministic=True, **kwargs)
                        finally:
                            expected['true_normalized'] = saved_true
                        assert torch.equal(other,result)
                        assert all(torch.equal(a,b) for a,b in zip(player.states[:2],outgoing[:2]))
                        player.states = outgoing
                        checks['privileged_invariance'] += env.num_envs
            expected['action'] = result.clone()
            rows.append(dict(prediction=prediction.cpu().numpy(), target=target.cpu().numpy(),
                             used=used.cpu().numpy(),actor_privileged=physical.cpu().numpy(),
                             true_privileged=truth.cpu().numpy(),initial=obs[:,:55].cpu().numpy(),
                             active=env.eval_active_mask.cpu().numpy().copy()))
            return result
        player.get_action = action
        return env, player
    wuji_goal_common.make_player = make_player
    oldargv = sys.argv
    try:
        sys.argv = [oldargv[0],'--checkpoint',str(teacher),'--output',str(args.output),
                    '--task','wuji_acquisition_bridge3_hemisphere','--hand','wuji_paper_official_actuator',
                    '--object','knife_wuji_bridge3_20260922','--initial-states',
                    str(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
                    '--stage-seconds',str(args.seconds),'--seed','20261060']
        if args.runtime_check:
            sys.argv += ['--initial-state-rows','0','100','200']
        from scripts.audit_wuji_timed_commands import main as audit
        audit()
    finally:
        sys.argv = oldargv
        wuji_goal_common.make_player = original
        if 'hook' in refs:
            refs['hook'].remove()
    assert tensor_digest(refs['model'].state_dict()) == refs['before_model']
    assert tensor_digest(refs['encoder'].state_dict()) == refs['before_encoder']
    report = json.loads((args.output/'report.json').read_text())
    assert checks['physics_transitions'] == report['num_envs']*report['recorded_steps']
    assert checks['latest_history_matches'] == checks['physics_transitions'] and checks['changed_history_rows'] > 0
    arrays = {k:np.stack([r[k] for r in rows]) for k in rows[0]}
    np.savez_compressed(args.output/'hybrid-trace.npz', **arrays)
    assert checks['actor_input_checks']==checks['physics_transitions']+checks['privileged_invariance']
    if args.runtime_check:assert checks['same_state_reference']==checks['physics_transitions']
    error = (arrays['prediction']-arrays['target'])*np.array(SCALES)
    rmse = np.sqrt(np.mean(error[arrays['active']]**2,axis=0)).tolist()
    audited = dict(status='passed',condition=args.condition,runtime=args.runtime_check,checks=checks,teacher_unchanged=True,encoder_unchanged=True,
                   student_sha256=metadata['sha256'], phase=artifact['phase'],update=artifact['update'],
                   rmse_physical=rmse,output_scales=artifact['output_scales'],fitting_provenance=artifact['fitting_provenance'],initial_fields='known initial acquisition-frame values',
                   current_privileged_actor_input=bool(truth_indices),privileged_components=truth_indices,
                   scope=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output/'hybrid-state-audit.json').write_text(json.dumps(audited,indent=2)+'\n')
    (args.output/'hybrid-source.py').write_bytes(Path(__file__).read_bytes())
    report.update(policy_kind='state_estimator_component_oracle_diagnostic',hybrid_state=audited)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
