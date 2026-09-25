"""Frozen camera-state estimator and frozen actor, with causal velocity estimation.

At t=0 use the known initial pose and zero slider/velocity, without a privileged
teacher action. From t=1 acquire a fresh RGB frame before every 30 Hz action.
Slider velocity is a causal low-pass finite difference (alpha=.25), identical
for the RGB and masked-image control. Current object/contact truth is saved for
scoring only and cannot enter the actor. The default initial states are development data;
an independently generated cohort must be supplied and identified separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import wuji_goal_common
from isaacgym import gymapi
import imageio.v2 as imageio
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.wuji_rgb_state_model import RGBStateModel, OUTPUT_SCALES
from scripts.wuji_physical_state_encoder import encode_target, decode_prediction, SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT = Path(__file__).resolve().parents[1]


def observable_features(obs):
    return obs[:, :96].clone()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seconds', type=int, choices=[2, 5], required=True)
    p.add_argument('--runtime-check', action='store_true')
    p.add_argument('--graphics-device-id', type=int, default=0)
    p.add_argument('--compute-device-id', type=int, default=None,
                   help='Explicit CUDA ordinal when CUDA devices are not masked.')
    p.add_argument('--ordered-cleanup', action='store_true',
                   help='Destroy all camera sensors before the existing simulation teardown.')
    p.add_argument('--verify-sensor-interface', action='store_true',
                   help='Compare an independent encoder/FK/RGB inference runtime; no hardware commands.')
    p.add_argument('--sensor-interface-driver', action='store_true',
                   help='Apply the sensor runtime actions to physics; reference is used only for numerical comparison.')
    p.add_argument('--sensor-matched-reference', action='store_true',
                   help='Compare both actor graphs on the same sensor/FK/estimated inputs; still audit sensor inputs against simulation separately.')
    p.add_argument('--sensor-active-parity', action='store_true',
                   help='Apply parity assertions only before an episode retires; retain retired rows as task failures and log their raw differences.')
    p.add_argument('--record-video', action='store_true',help='Save the actual pre-action camera frames without text.')
    p.add_argument('--collect-rgb-data', action='store_true', help='Save causal pre-action images/labels for later fitting; does not update this policy.')
    p.add_argument('--initial-state-rows', type=int, nargs='+')
    p.add_argument('--initial-states',type=Path,default=ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy')
    p.add_argument('--evaluation-seed',type=int,default=20261060)
    args = p.parse_args()
    assert not args.sensor_interface_driver or args.verify_sensor_interface
    assert not args.sensor_matched_reference or args.sensor_interface_driver
    assert not args.sensor_active_parity or args.sensor_matched_reference
    assert not args.output.exists(); args.output.mkdir(parents=True)
    sha = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    assert sha == json.loads(args.artifact.with_suffix('.json').read_text())['sha256']
    artifact = torch.load(args.artifact, map_location='cpu')
    arm = artifact['arm']; assert arm in ['rgb', 'masked']
    assert artifact['update'] == 5000
    teacher_sha = hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest()
    assert all(s['teacher_sha256'] == teacher_sha for s in artifact['provenance']['sources'])
    torch.set_num_threads(4)
    original = wuji_goal_common.make_player
    refs = {}; rows = []; collection=[];chunks=[]
    checks = dict(physics_transitions=0,privileged_invariance=0,camera_frames=0,
        action_target_max_error=0.,actor_encoder_replacements=0,masked_image_invariance=0,
        initial_known_state_rows=0)
    atomic_json(args.output/'status.json',dict(status='initializing',started=now(),arm=arm))
    (args.output/'source-rgb-policy.py').write_bytes(Path(__file__).read_bytes())

    def flush_collection():
        if not collection:return
        folder=args.output/'rgb-data';folder.mkdir(exist_ok=True)
        path=folder/f'frames-{len(chunks):04d}.npz'
        np.savez_compressed(path,**{k:np.stack([row[k] for row in collection]) for k in collection[0]})
        chunks.append(dict(path=str(path.relative_to(args.output)),frames=len(collection),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        collection.clear()

    def make_player(cfg, path):
        cfg.graphics_device_id=args.graphics_device_id;cfg.task.env.enableCameraSensors=True
        if args.compute_device_id is not None:
            torch.cuda.set_device(args.compute_device_id)
            cfg.sim_device=cfg.rl_device='cuda:'+str(args.compute_device_id)
        env, player = original(cfg, path)
        (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
        model = player.model.eval()
        assert model.a2c_network.policy_obs_dim == 111
        estimator = RGBStateModel(artifact['feature_mean'], artifact['feature_scale']).to(player.device).eval()
        estimator.load_state_dict(artifact['state_dict'])
        for network in [model, estimator]:
            for parameter in network.parameters(): parameter.requires_grad_(False)
        refs.update(model=model,estimator=estimator,before_model=tensor_digest(model.state_dict()),before_estimator=tensor_digest(estimator.state_dict()))
        if args.verify_sensor_interface:
            from isaacgymenvs.deploy.wuji.rgb_policy_runtime import WujiRGBPolicyRuntime
            assert env.joint_noise==0
            # The additional model construction must not change simulation RNG.
            with torch.random.fork_rng(devices=[env.device_id]):
                refs['sensor_runtime']=WujiRGBPolicyRuntime(cfg,ROOT/TEACHER,args.artifact,
                                                           control_dt=env.dt*env.control_freq_inv)
            checks.update(sensor_interface_rows=0,sensor_policy_obs_max_error=0.,
                          sensor_state_max_error=0.,sensor_action_max_error=0.,sensor_target_max_error=0.,
                          sensor_driver_rows=0)
            if args.sensor_active_parity:
                checks.update(sensor_active_rows=0,sensor_retired_rows=0,sensor_retired_ids=[])
        props = env.object_cfg['default_props']
        properties = torch.tensor(list(props['mass'])+[props['friction'],props['dof_damping'],props.get('dof_stiffness',0.)],device=player.device).reshape(1,5)
        cameras=[];center=np.array([0.,-.085,.525]);offset=np.array([0.,.25,.12])
        if args.ordered_cleanup:
            cleanup=dict(status='pending',camera_count=0,sim_destroy_returned=False)
            def before_destroy():
                cleanup.update(status='synchronizing',started=now())
                atomic_json(args.output/'cleanup-status.json',cleanup)
                torch.cuda.synchronize(player.device)
                task_cameras=[int(cam) for cam in env.cam_handle_list]
                for handles in (cameras,task_cameras):
                    for handle,camera in zip(env.envs,handles):
                        env.gym.destroy_camera_sensor(env.sim,handle,camera)
                        cleanup['camera_count']+=1
                torch.cuda.synchronize(player.device)
                cleanup.update(status='cameras_destroyed',finished=now())
                atomic_json(args.output/'cleanup-status.json',cleanup)
            def after_destroy():
                cleanup.update(status='completed',sim_destroy_returned=True,finished=now())
                atomic_json(args.output/'cleanup-status.json',cleanup)
            env.before_audit_destroy_sim=before_destroy
            env.after_audit_destroy_sim=after_destroy
        for handle in env.envs:
            settings=gymapi.CameraProperties();settings.width=settings.height=320;settings.horizontal_fov=45.
            camera=env.gym.create_camera_sensor(handle,settings);assert camera>=0
            env.gym.set_camera_location(camera,handle,gymapi.Vec3(*(center+offset)),gymapi.Vec3(*center))
            cameras.append(camera)
        if args.record_video:
            assert env.num_envs<=3,'Video is restricted to explicitly selected small batches'
            refs['video_writer']=imageio.get_writer(args.output/'policy-no-text.mp4',fps=30)
            checks['video_frames']=0
        actual = player.get_action; expected = {}
        def hook(module, inputs):
            checks['actor_encoder_replacements'] += env.num_envs
            return (expected['normalized'],)
        refs['hook'] = model.a2c_network.priv_encoder.register_forward_pre_hook(hook)
        pre = env.pre_physics_step
        def pre_step(action):
            pre(action)
            assert torch.equal(env.actions,expected['action'])
            error=float((env.cur_targets[:,:20]-expected['targets']).abs().max())
            assert error<1e-6,error
            checks['action_target_max_error']=max(checks['action_target_max_error'],error)
            checks['physics_transitions']+=env.num_envs
        env.pre_physics_step=pre_step
        dt = env.dt*env.control_freq_inv
        assert abs(dt-1/30)<1e-7
        def infer_sensor(obs,x,images,step):
            runtime=refs['sensor_runtime']
            if step==0:runtime.reset(obs[:,:55],env.init_targets[:,:20])
            history={} if args.sensor_interface_driver else dict(
                applied_previous_action=x[:,75:95],commanded_previous_targets=env.prev_targets[:,:20])
            incoming=[v.clone() for v in runtime.player.states]
            with torch.random.fork_rng(devices=[env.device_id]):
                sensor=runtime.infer(env.hand_dof_pos.detach().cpu().numpy(),images,
                                     x[:,95:96].detach().cpu().numpy(),**history)
            return sensor,incoming

        def action(obs,is_deterministic=False,**kwargs):
            assert is_deterministic
            step=len(rows);x=observable_features(obs)
            with torch.no_grad():
                if step==0:
                    values=obs.new_zeros((env.num_envs,8))
                    images=None;checks['initial_known_state_rows']+=env.num_envs
                else:
                    env.gym.fetch_results(env.sim,True);env.gym.step_graphics(env.sim);env.gym.render_all_camera_sensors(env.sim)
                    images=np.stack([np.asarray(env.gym.get_camera_image(env.sim,handle,cam,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(320,320,4)[...,:3].copy() for handle,cam in zip(env.envs,cameras)])
                    assert (images.reshape(env.num_envs,-1).max(-1)>0).all()
                    if args.record_video:
                        refs['video_writer'].append_data(np.concatenate(images,axis=1))
                        checks['video_frames']+=1
                    rgb=torch.tensor(images,device=player.device).permute(0,3,1,2).float()/255.-.5
                    prediction=estimator(rgb,x,mask_image=arm=='masked')*x.new_tensor(OUTPUT_SCALES)
                    velocity=.75*expected['values'][:,7]+.25*(prediction[:,6]-expected['values'][:,6])/dt
                    values=torch.cat([prediction,velocity[:,None]],-1)
                    checks['camera_frames']+=env.num_envs
                    if args.runtime_check and arm=='masked':
                        other=estimator(rgb.flip(-1),x,mask_image=True)*x.new_tensor(OUTPUT_SCALES)
                        assert torch.equal(other,prediction)
                        checks['masked_image_invariance']+=env.num_envs
                    if step in [1,151,301,451]:
                        imageio.imwrite(args.output/f'camera-step{step:04d}-no-text.png',np.concatenate(images[:3],axis=1))
                assert torch.isfinite(values).all()
                sensor=None;reference_obs=obs;reference_values=values
                if args.sensor_matched_reference:
                    sensor,sensor_incoming=infer_sensor(obs,x,images,step)
                    # URDF FK and PhysX link transforms differ by micrometres.
                    # Compare actor implementations on identical inputs and
                    # independent recurrent histories. Input differences are
                    # still checked separately against the original simulator
                    # observation/estimator at the unchanged tolerances below.
                    reference_obs=obs.clone()
                    reference_obs[:,:111]=sensor['policy_observation']
                    reference_values=sensor['estimated_state']
                physical=decode_prediction(reference_obs[:,:55],reference_values/reference_values.new_tensor(SCALES),properties)
                modified=reference_obs.clone();modified[:,111:132]=physical
                expected['normalized']=model.norm_obs(player._preproc_obs(modified))[:,111:132]
                incoming=[v.clone() for v in player.states]
                result=actual(reference_obs,is_deterministic=True,**kwargs)
                outgoing=[v.clone() for v in player.states]
                if args.runtime_check or step==0:
                    changed=reference_obs.clone();changed[:,111:137]+=17.
                    assert torch.equal(observable_features(changed),observable_features(reference_obs))
                    player.states=incoming
                    other=actual(changed,is_deterministic=True,**kwargs)
                    assert torch.equal(other,result)
                    assert all(torch.equal(a,b) for a,b in zip(outgoing[:2],player.states[:2]))
                    player.states=outgoing;checks['privileged_invariance']+=env.num_envs
                assert result.shape==(env.num_envs,20) and torch.isfinite(result).all()
                expected.update(action=result.clone(),targets=env.actions_to_targets(result).clone(),values=values.clone())
                if args.verify_sensor_interface:
                    if sensor is None:sensor,sensor_incoming=infer_sensor(obs,x,images,step)
                    parity_mask=env.eval_active_mask.bool() if args.sensor_active_parity else torch.ones(env.num_envs,device=player.device,dtype=torch.bool)
                    if args.sensor_active_parity:
                        checks['sensor_active_rows']+=int(parity_mask.sum())
                        checks['sensor_retired_rows']+=int((~parity_mask).sum())
                        checks['sensor_retired_ids']=sorted(set(checks['sensor_retired_ids'])|set((~parity_mask).nonzero().flatten().cpu().tolist()))
                    for key,left,right,tolerance in [
                        ('sensor_policy_obs_max_error',sensor['policy_observation'],obs[:,:111],2e-5),
                        ('sensor_state_max_error',sensor['estimated_state'],values,2e-5),
                        ('sensor_action_max_error',sensor['action'],result,2e-4),
                        ('sensor_target_max_error',sensor['joint_targets'],expected['targets'],2e-4)]:
                        difference=(left-right).abs()
                        if args.sensor_active_parity:
                            raw_key=key+'_including_retired'
                            checks[raw_key]=max(checks.get(raw_key,0.),float(difference.max()))
                        error=float(difference[parity_mask].max()) if bool(parity_mask.any()) else 0.
                        checks[key]=max(checks[key],error)
                        if error>=tolerance:
                            # Preserve the first discrepancy, including both recurrent
                            # histories, so FK/input and actor arithmetic can be isolated
                            # offline without changing the frozen policy or thresholds.
                            torch.save(dict(step=step,key=key,error=error,tolerance=tolerance,
                                comparison_left=left.detach().cpu(),comparison_right=right.detach().cpu(),
                                physics_observation=obs.detach().cpu(),
                                evaluation_active=env.eval_active_mask.detach().cpu(),
                                at_reset_ids=env.at_reset_ids.detach().cpu(),
                                reset_buf=env.reset_buf.detach().cpu(),
                                reference_observation=reference_obs.detach().cpu(),
                                reference_action=result.detach().cpu(),
                                reference_values=values.detach().cpu(),
                                reference_normalized_privileged=expected['normalized'].detach().cpu(),
                                reference_incoming=[v.detach().cpu() for v in incoming],
                                sensor_incoming=[v.detach().cpu() for v in sensor_incoming],
                                sensor={k:v.detach().cpu() for k,v in sensor.items()},
                                joints=env.hand_dof_pos.detach().cpu()),
                                args.output/'sensor-first-discrepancy.pth')
                        assert error<tolerance,(key,error,tolerance)
                    checks['sensor_interface_rows']+=env.num_envs
                    if args.sensor_interface_driver:
                        result=sensor['action'];values=sensor['estimated_state']
                        targets=env.actions_to_targets(result)
                        assert float((targets-sensor['joint_targets']).abs().max())<1e-6
                        expected.update(action=result.clone(),targets=targets.clone(),values=values.clone())
                        checks['sensor_driver_rows']+=env.num_envs
                # Labels are read only after action calculation and never fed back.
                truth=encode_target(obs[:,:55],obs[:,111:132])*obs.new_tensor(SCALES)
                if args.collect_rgb_data and step>=1 and (args.runtime_check or step%3==1):
                    collection.append(dict(step=np.int32(step),rgb=images.copy(),
                        known_initial=x[:,:55].cpu().numpy().copy(),proprio=x[:,55:95].cpu().numpy().copy(),
                        goal=x[:,95:96].cpu().numpy().copy(),target=truth.cpu().numpy().copy(),
                        active=env.eval_active_mask.cpu().numpy().copy()))
                    if len(collection)>=20:flush_collection()
                rows.append(dict(prediction=values.cpu().numpy().copy(),truth=truth.cpu().numpy().copy(),
                    features=x.cpu().numpy().copy(),active=env.eval_active_mask.cpu().numpy().copy()))
            if step%30==0:
                atomic_json(args.output/'status.json',dict(status='evaluating',arm=arm,step=step,heartbeat=now(),checks=checks))
            return result
        player.get_action=action
        return env,player

    wuji_goal_common.make_player=make_player;argv=sys.argv
    try:
        sys.argv=[argv[0],'--checkpoint',str(ROOT/TEACHER),'--output',str(args.output),
            '--task','wuji_acquisition_bridge3_hemisphere','--hand','wuji_paper_official_actuator',
            '--object','knife_wuji_bridge3_20260922','--initial-states',str(args.initial_states),
            '--stage-seconds',str(args.seconds),'--seed',str(args.evaluation_seed)]
        selected=args.initial_state_rows or ([0,100,200] if args.runtime_check else None)
        if selected:sys.argv+=['--initial-state-rows']+list(map(str,selected))
        from scripts.audit_wuji_timed_commands import main as evaluate
        evaluate()
        if args.record_video:
            refs.pop('video_writer').close()
            assert checks['video_frames']==599
        assert tensor_digest(refs['model'].state_dict())==refs['before_model']
        assert tensor_digest(refs['estimator'].state_dict())==refs['before_estimator']
        report=json.loads((args.output/'report.json').read_text())
        if args.collect_rgb_data:
            flush_collection()
            frames=sum(row['frames'] for row in chunks)
            assert frames==(599 if args.runtime_check else 200)
            selected=report['initial_state_rows']
            atomic_json(args.output/'collection-status.json',dict(status='completed',finished=now(),
                chunks=chunks,frames=frames,images=frames*len(selected),selected_initial_rows=selected,
                training_rows=[i for i in selected if i%100<20],validation_rows=[i for i in selected if i%100>=20],
                physics_collection_policy='learned_'+arm+'_state_policy',actor_artifact_sha256=sha,
                teacher_sha256=teacher_sha,clock_seconds=args.seconds,physics_transitions=600*len(selected),
                camera=dict(center=[0.,-.085,.525],offset=[0.,.25,.12],resolution=[320,320],horizontal_fov=45),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                trained_during_collection=False,scope='Own-state sensor labels after frozen learned-policy decisions. Inactive rows retained for audit and excluded from fitting.'))
        assert checks['physics_transitions']==report['num_envs']*600
        assert checks['camera_frames']==report['num_envs']*599
        arrays={k:np.stack([row[k] for row in rows]) for k in rows[0]}
        np.savez_compressed(args.output/'rgb-estimation-trace.npz',**arrays)
        expected_velocity=np.zeros_like(arrays['prediction'][...,7])
        for t in range(1,600):expected_velocity[t]=.75*expected_velocity[t-1]+.25*(arrays['prediction'][t,:,6]-arrays['prediction'][t-1,:,6])*30
        assert np.allclose(expected_velocity,arrays['prediction'][...,7],atol=1e-6)
        error=arrays['prediction']-arrays['truth']
        audit=dict(status='passed',finished=now(),arm=arm,artifact_sha256=sha,teacher_sha256=teacher_sha,
            checks=checks,model_unchanged=True,estimator_unchanged=True,current_truth_actor_input=False,
            causal_velocity_recomputed=True,rmse=np.sqrt(np.mean(error[arrays['active']]**2,axis=0)).tolist(),
            scope=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        audit['sensor_interface_driver']=args.sensor_interface_driver
        audit['sensor_matched_reference']=args.sensor_matched_reference
        audit['sensor_active_parity']=args.sensor_active_parity
        atomic_json(args.output/'rgb-policy-audit.json',audit)
        atomic_json(args.output/'environment-setup-report.json',report)
        report.update(policy_kind='frozen_'+arm+'_state_estimator_and_actor',checkpoint_sha256=sha,
            actor_sha256=teacher_sha,current_object_truth_actor_input=False,scope=__doc__)
        report['sensor_interface_driver']=args.sensor_interface_driver
        report['sensor_matched_reference']=args.sensor_matched_reference
        report['sensor_active_parity']=args.sensor_active_parity
        atomic_json(args.output/'report.json',report)
        atomic_json(args.output/'status.json',dict(status='completed',finished=now(),arm=arm,checks=checks))
    except BaseException as exc:
        atomic_json(args.output/'status.json',dict(status='failed',finished=now(),error=repr(exc),checks=checks));raise
    finally:
        sys.argv=argv;wuji_goal_common.make_player=original
        if 'hook' in refs:refs['hook'].remove()
        if 'video_writer' in refs:refs['video_writer'].close()


if __name__=='__main__':main()
