"""Evaluate a state estimator fitted on frozen teacher trajectories, without a teacher rollout prefix."""
import argparse
import hashlib
import json
import os
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
    p.add_argument('--custom-command-tcn', action='store_true',
                   help='Copy unchanged command-base weights to the existing custom TCN; establishes a separate numerical baseline.')
    p.add_argument('--collect-history', action='store_true', help='Save fixed development train/validation rows for offline dataset aggregation.')
    args = p.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    metadata = json.loads(args.artifact.with_suffix('.json').read_text())
    assert hashlib.sha256(args.artifact.read_bytes()).hexdigest() == metadata['sha256']
    artifact = torch.load(args.artifact, map_location='cpu')
    teacher = ROOT/TEACHER
    assert hashlib.sha256(teacher.read_bytes()).hexdigest() == artifact['teacher_sha256']
    assert artifact['phase'] in ('offline_teacher_fit', 'offline_slider_fusion', 'offline_command_slider')
    assert not args.custom_command_tcn or artifact['phase'] == 'offline_command_slider'
    assert len(artifact['output_scales']) == 8
    original = wuji_goal_common.make_player
    refs = {}
    checks = dict(physics_transitions=0, privileged_invariance=0, teacher_physics_transitions=0,
                  latest_history_matches=0, changed_history_rows=0)
    rows = []
    history_rows = []
    selected = np.array([base+i for base in [0,100,200] for i in range(30)])
    assert not (args.collect_history and args.runtime_check)
    def make_player(cfg, path):
        cfg.task.env.proprioHistoryLen = 50
        OmegaConf.update(cfg, 'task.env.enableStudentEncoderObs', True, force_add=True)
        if artifact['phase']=='offline_command_slider':
            # Fix inference arithmetic across the matched GPU arms. Legacy
            # evaluations retain their original numerical protocol.
            os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
            cfg.torch_deterministic=True
            torch.backends.cudnn.benchmark=False
            torch.backends.cudnn.deterministic=True
            torch.backends.cudnn.allow_tf32=False
            torch.backends.cuda.matmul.allow_tf32=False
            torch.use_deterministic_algorithms(True)
        env, player = original(cfg, path)
        if artifact['phase']=='offline_command_slider':
            # rl_games Runner.__init__ enables cudnn.benchmark while loading.
            # Reapply before any estimator or actual policy inference.
            torch.backends.cudnn.benchmark=False
            torch.backends.cudnn.deterministic=True
            torch.backends.cudnn.allow_tf32=False
            torch.backends.cuda.matmul.allow_tf32=False
            torch.use_deterministic_algorithms(True)
            assert not torch.backends.cudnn.benchmark and torch.backends.cudnn.deterministic
            assert torch.are_deterministic_algorithms_enabled()
            assert not torch.backends.cuda.matmul.allow_tf32 and not torch.backends.cudnn.allow_tf32
        (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
        assert env.student_encoder_obs_enabled and env.joint_noise == 0
        model = player.model.eval()
        with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
            if args.custom_command_tcn:
                from scripts.wuji_command_slider import make_custom_command_base
                encoder = make_custom_command_base(artifact)
            else:
                encoder, _ = make_encoder(artifact['encoder_spec'])
                encoder.load_state_dict(artifact['state_encoder'])
            if artifact['phase'] == 'offline_slider_fusion':
                from scripts.wuji_slider_fusion import SliderFusionEncoder
                encoder = SliderFusionEncoder(encoder, artifact)
            elif artifact['phase'] == 'offline_command_slider':
                from scripts.wuji_command_slider import CommandSliderEncoder
                encoder = CommandSliderEncoder(encoder, artifact)
            encoder.to(player.device).eval()
        props = torch.tensor(artifact['nominal_properties'], device=player.device).reshape(1,5)
        selected_tensor = torch.tensor(selected, device=player.device) if args.collect_history else None
        unit_ratio = torch.tensor(artifact['output_scales'], device=player.device) / torch.tensor(SCALES, device=player.device)
        refs.update(model=model, encoder=encoder, before_model=tensor_digest(model.state_dict()),
                    before_encoder=tensor_digest(encoder.state_dict()))
        actual = player.get_action
        expected = {}
        def hook(module, inputs):
            return (expected['normalized'],)
        refs['hook'] = model.a2c_network.priv_encoder.register_forward_pre_hook(hook)
        pre = env.pre_physics_step
        def pre_step(action):
            pre(action)
            assert torch.equal(env.actions, expected['action'])
            if artifact['phase']=='offline_command_slider':
                desired=env.init_targets[:,:20]+.04*action
                desired[:,16:]=expected['controller_targets'][:,16:]+.025*action[:,16:]
                desired=torch.maximum(torch.minimum(desired,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
                error=float((desired-env.cur_targets[:,:20]).abs().max())
                assert error<1e-6,error
                checks['command_update_max_error_rad']=max(checks.get('command_update_max_error_rad',0.),error)
                checks['command_update_rows']=checks.get('command_update_rows',0)+env.num_envs
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
                if artifact['phase']=='offline_command_slider':
                    expected['controller_targets']=env.cur_targets[:,:20].clone()
                    if not rows:
                        assert torch.equal(expected['controller_targets'],env.init_targets[:,:20])
                    prediction=encoder(inputs,expected['controller_targets'])*unit_ratio
                    if artifact['update']==0:
                        assert torch.equal(prediction,encoder.base(inputs)*unit_ratio)
                        checks['zero_residual_rows']=checks.get('zero_residual_rows',0)+env.num_envs
                else:
                    prediction = encoder(inputs) * unit_ratio
                if args.runtime_check and artifact['phase'] == 'offline_slider_fusion':
                    from scripts.analyze_wuji_kinematic_slider import pad_poses
                    positions = pad_poses(encoder.kinematics,inputs[:,1960:1980].cpu().numpy().astype(np.float64))[...,:3,3]
                    measured = obs[:,96:111].cpu().numpy().reshape(-1,5,3)
                    error = float(np.abs(positions-measured).max())
                    assert error < 5e-5, error
                    checks['fk_pad_max_error_m'] = max(checks.get('fk_pad_max_error_m',0.),error)
                    checks['fk_pad_compared_rows'] = checks.get('fk_pad_compared_rows',0)+env.num_envs
                physical = decode_prediction(obs[:, :55], prediction, props)
                modified = obs.clone()
                modified[:,111:132] = physical
                expected['normalized'] = model.norm_obs(player._preproc_obs(modified))[:,111:132]
                incoming = [v.clone() for v in player.states]
                result = actual(obs, is_deterministic=True, **kwargs)
                outgoing = [v.clone() for v in player.states]
                if args.runtime_check or not rows:
                    changed = obs.clone()
                    changed[:,111:137] += 7.
                    assert torch.equal(history_input(env.proprioception_buf, changed), inputs)
                    if artifact['phase']=='offline_command_slider':
                        other_prediction=encoder(history_input(env.proprioception_buf,changed),expected['controller_targets'])*unit_ratio
                        assert torch.equal(other_prediction,prediction)
                        altered=expected['controller_targets']+.03
                        altered_prediction=encoder(inputs,altered)*unit_ratio
                        if artifact['command_arm']=='masked':assert torch.equal(altered_prediction,prediction)
                        checks['controller_input_changed_rows']=checks.get('controller_input_changed_rows',0)+int((altered_prediction!=prediction).any(-1).sum())
                        checks['controller_input_checked_rows']=checks.get('controller_input_checked_rows',0)+env.num_envs
                    else:
                        assert torch.equal(encoder(history_input(env.proprioception_buf, changed)) * unit_ratio, prediction)
                    player.states = incoming
                    other = actual(changed, is_deterministic=True, **kwargs)
                    assert torch.equal(other, result)
                    assert all(torch.equal(a,b) for a,b in zip(outgoing[:2], player.states[:2]))
                    player.states = outgoing
                    checks['privileged_invariance'] += env.num_envs
                target = encode_target(obs[:, :55], obs[:,111:132])
            expected['action'] = result.clone()
            if args.collect_history and len(rows) % 4 == 0:
                history_rows.append(dict(history=inputs[selected_tensor].cpu().numpy().copy(),
                    target=(target[selected_tensor]*target.new_tensor(SCALES)).cpu().numpy().copy(),
                    active=env.eval_active_mask[selected_tensor].cpu().numpy().copy(), step=len(rows)))
            rows.append(dict(prediction=prediction.cpu().numpy(), target=target.cpu().numpy(),
                             active=env.eval_active_mask.cpu().numpy().copy()))
            if artifact['phase']=='offline_command_slider':
                rows[-1]['controller_targets']=expected['controller_targets'].cpu().numpy().copy()
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
    if artifact['phase']=='offline_command_slider':
        assert checks['command_update_rows']==checks['physics_transitions']
        if artifact['update']==0:assert checks['zero_residual_rows']==checks['physics_transitions']
        if artifact['command_arm']=='masked':assert checks['controller_input_changed_rows']==0
        elif artifact['update']>0:assert checks['controller_input_changed_rows']>0
    arrays = {k:np.stack([r[k] for r in rows]) for k in rows[0]}
    np.savez_compressed(args.output/'estimation-trace.npz', **arrays)
    error = (arrays['prediction']-arrays['target'])*np.array(SCALES)
    rmse = np.sqrt(np.mean(error[arrays['active']]**2,axis=0)).tolist()
    audited = dict(status='passed',checks=checks,teacher_unchanged=True,encoder_unchanged=True,
                   student_sha256=metadata['sha256'], phase=artifact['phase'],update=artifact['update'],
                   rmse_physical=rmse,output_scales=artifact['output_scales'],fitting_provenance=artifact['fitting_provenance'],initial_fields='known initial acquisition-frame values',
                   current_privileged_actor_input=False,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if artifact['phase']=='offline_command_slider':
        audited['state_encoder_backend'] = 'custom_tcn' if args.custom_command_tcn else 'torch_conv1d'
        audited.update(command_arm=artifact['command_arm'],additional_input='20 current own commanded targets, preceding this action; current object/contact values excluded.')
        audited['numerical_protocol']=dict(cublas_workspace=os.environ['CUBLAS_WORKSPACE_CONFIG'],
            deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),cudnn_benchmark=torch.backends.cudnn.benchmark,
            cudnn_deterministic=torch.backends.cudnn.deterministic,cudnn_tf32=torch.backends.cudnn.allow_tf32,
            matmul_tf32=torch.backends.cuda.matmul.allow_tf32)
    (args.output/'state-estimation-audit.json').write_text(json.dumps(audited,indent=2)+'\n')
    report.update(policy_kind=('student_with_slider_fusion' if artifact['phase']=='offline_slider_fusion'
                               else 'student_with_command_slider' if artifact['phase']=='offline_command_slider'
                               else 'student_with_offline_fitted_physical_state'),state_estimation=audited)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.collect_history:
        assert report['num_envs'] == 332 and report['recorded_steps'] == 600 and len(history_rows) == 150
        data = {k:np.stack([r[k] for r in history_rows]) for k in history_rows[0]}
        data.update(initial_rows=selected, train_rows=selected%100 < 20)
        dataset = args.output/'history-state-pairs.npz'
        np.savez_compressed(dataset, **data)
        manifest = dict(status='passed', seconds=args.seconds, collection_policy='frozen_state_estimator',
            source_teacher_sha256=artifact['teacher_sha256'], student_sha256=metadata['sha256'],
            teacher_unchanged=True, encoder_unchanged=True, current_privileged_actor_input=False,
            dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(), checks=checks,
            initial_rows=selected.tolist(), train_samples=int((data['active'] & data['train_rows'][None,:]).sum()),
            validation_samples=int((data['active'] & ~data['train_rows'][None,:]).sum()),
            split='Same fixed 60 training / 30 validation development rows as teacher collection; every fourth frame. The30 validation rows are excluded from fitting. The332 physical development evaluation includes fitting rows.',
            label='physical displacement3/worldrotationvector3/sliderdisplacement/velocity; SI units',
            scope='Frozen student own-trajectory collection; current truth supplies supervised labels only. Reused development states.',
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    main()
