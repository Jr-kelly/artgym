"""Independent closed-loop rollout with physical traces and optional text-free video.

Uses the official consecutive evaluator's goal switching and termination. No
demonstration trajectory is loaded or provided to the policy.
"""
import argparse,json,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
from isaacgymenvs.student_eval_utils import run_grasp_evaluation_loop
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
from omegaconf import OmegaConf
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--student-artifact',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=100)
    p.add_argument('--seed',type=int,default=505);p.add_argument('--steps',type=int,default=600)
    p.add_argument('--task',default='wuji_acquisition');p.add_argument('--override',action='append',default=[])
    p.add_argument('--instance',default='000');p.add_argument('--grasp-split',default='train')
    p.add_argument('--episodes-per-grasp',type=int,
        help='For a multi-grasp pool, require envs = pool size times this count.')
    p.add_argument('--grasp-index',type=int)
    p.add_argument('--initial-states',type=Path,help='Use explicitly saved states from a prior perturbation audit.')
    p.add_argument('--initial-state-rows',type=int,nargs='+',help='Exactly one saved-state row for each parallel environment.')
    p.add_argument('--perturb-position-mm',type=float,default=0.)
    p.add_argument('--perturb-joint-rad',type=float,default=0.)
    p.add_argument('--perturb-rotation-deg',type=float,default=0.)
    p.add_argument('--stochastic',action='store_true',help='Sample policy actions to diagnose a train/eval action-distribution gap.')
    p.add_argument('--acquisition-knife-frame',action='store_true',
        help='Convert original-axis knife observations to the acquisition asset convention; physics unchanged.')
    p.add_argument('--thumb-tracking-limit',type=float,
        help='Execution-only diagnosis: cap thumb joint2 target error relative to actual angle (radians).')
    p.add_argument('--video-all-envs',action='store_true',help='Record a text-free grid of at most six parallel environments.')
    p.add_argument('--video',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if a.initial_state_rows is not None and a.initial_states is None:
        raise ValueError('Saved-state rows require an explicit initial-state file')
    if a.acquisition_knife_frame and a.student_artifact:
        raise ValueError('This frame diagnostic currently supports teachers only')
    if a.video_all_envs:
        if not 1<=a.envs<=6:raise ValueError('Video grids support one to six explicitly selected environments')
        a.video=True
    audit_source=Path(__file__).read_bytes()
    audit_source_sha256=hashlib.sha256(audit_source).hexdigest()
    (a.output/'source_audit_wuji_checkpoint.py').write_bytes(audit_source)
    overrides=['object=knife_wuji_acquisition',f'task.env.episodeLength={a.steps}','test=True']+a.override
    if a.video:overrides+=['graphics_device_id=0','task.env.enableCameraSensors=True',
        'task.env.camera.width=960','task.env.camera.height=720',
        'task.env.camera.cam_pos=[-0.10,-0.16,0.75]','task.env.camera.cam_target=[0.0,-0.085,0.525]']
    if a.video_all_envs:overrides+=['task.env.camera.width=512','task.env.camera.height=384']
    cfg=configuration(a.task,a.envs,overrides,train='wujiAcquisitionSAPG',seed=a.seed)
    (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env,player=make_player(cfg,a.checkpoint)
    frame_adapter_sha256=None
    if a.acquisition_knife_frame:
        from scripts.wuji_knife_frame import install_original_knife_frame_adapter
        install_original_knife_frame_adapter(env)
        frame_source=(Path(__file__).parent/'wuji_knife_frame.py').read_bytes()
        frame_adapter_sha256=hashlib.sha256(frame_source).hexdigest()
        (a.output/'source_wuji_knife_frame.py').write_bytes(frame_source)
    intervention_source_sha256=None
    if a.thumb_tracking_limit is not None:
        from scripts.wuji_control_interventions import install_thumb_tracking_limit
        if cfg.hand.dof_names[17] != 'hand_r_thumb_joint2':
            raise ValueError('Diagnostic control intervention requires the explicit ArtBot joint order')
        install_thumb_tracking_limit(env,a.thumb_tracking_limit)
        intervention_source=(Path(__file__).parent/'wuji_control_interventions.py').read_bytes()
        intervention_source_sha256=hashlib.sha256(intervention_source).hexdigest()
        (a.output/'source_wuji_control_interventions.py').write_bytes(intervention_source)
    if a.student_artifact is not None:
        from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
        from isaacgymenvs.eval_common import preprocess_train_config
        artifact=torch.load(a.student_artifact,map_location='cpu');metadata=artifact['distill_meta']
        if metadata['task']!=a.task or metadata['hand']!='wuji_paper':
            raise ValueError('Student identity does not match the requested audit')
        student_encoder,_,_,_=build_student_encoder_from_artifact(player,cfg,
            preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),artifact,metadata)
        player.model.a2c_network.priv_encoder=student_encoder;player.model.eval()
        env.set_student_encoder_obs_enabled(True)
    saved_initial_state_sha256=None
    if a.initial_states is not None:
        if a.grasp_index is not None or any([a.perturb_position_mm,a.perturb_joint_rad,a.perturb_rotation_deg]):
            raise ValueError('Saved-state replay cannot be combined with a grasp index or new perturbation')
        states=np.load(a.initial_states)
        rows=a.initial_state_rows if a.initial_state_rows is not None else list(range(len(states)))
        if len(rows)!=a.envs or min(rows)<0 or max(rows)>=len(states):
            raise ValueError('Saved-state row count/bounds do not match the declared environment batch')
        selected=states[rows]
        if not np.isfinite(selected).all():raise ValueError('Nonfinite saved initial state')
        env.configure_fixed_grasp_consecutive_evaluation(instance_id=a.instance,grasp_state=selected[0],
            goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=a.envs)
        if selected.shape!=tuple(env.eval_grasp_states.shape):raise ValueError('Saved-state layout differs from task')
        env.eval_grasp_states[:]=torch.as_tensor(selected,device=env.device)
        np.save(a.output/'selected_initial_states.npy',selected)
        saved_initial_state_sha256=hashlib.sha256(a.initial_states.read_bytes()).hexdigest()
    elif a.grasp_index is None:
        env.configure_grasp_consecutive_evaluation(instance_id=a.instance,goal_sequence=tuple(cfg.object.task.goals),
            grasp_split=a.grasp_split,episodes_per_grasp=a.episodes_per_grasp or a.envs)
    else:
        index=env.instance_id_list.index(a.instance)
        pool=env._get_eval_grasp_states_for_split(index,a.grasp_split)
        if not 0<=a.grasp_index<len(pool):raise ValueError('Selected grasp index outside the requested split')
        selected=pool[a.grasp_index].cpu().numpy().copy()
        np.save(a.output/'selected_initial_state.npy',selected)
        env.configure_fixed_grasp_consecutive_evaluation(instance_id=a.instance,grasp_state=selected,
            goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=a.envs)
    if env.eval_episodes_per_grasp!=1:
        raise ValueError('Physical trace audits require one trial per environment; expand parallel envs explicitly')
    if any([a.perturb_position_mm,a.perturb_joint_rad,a.perturb_rotation_deg]):
        from scipy.spatial.transform import Rotation
        from scripts.wuji_kinematics import WujiKinematics
        rng=np.random.default_rng(a.seed);hand=WujiKinematics()
        states=env.eval_grasp_states.cpu().numpy().copy()
        low=env.hand_dof_lower_limits.cpu().numpy();high=env.hand_dof_upper_limits.cpu().numpy()
        for state in states:
            delta=rng.uniform(-a.perturb_joint_rad,a.perturb_joint_rad,20)
            state[:20]=np.clip(state[:20]+delta,low,high)
            state[20:40]=np.clip(state[20:40]+delta,low,high)
            translation=rng.uniform(-a.perturb_position_mm,a.perturb_position_mm,3)/1000
            rotation=Rotation.from_rotvec(np.deg2rad(rng.uniform(-a.perturb_rotation_deg,a.perturb_rotation_deg,3)))
            state[47:50]=state[40:43]+translation+rotation.apply(state[47:50]-state[40:43])
            state[40:43]+=translation
            for start in [43,50]:state[start:start+4]=(rotation*Rotation.from_quat(state[start:start+4])).as_quat()
            fk=hand.forward(state[:20]);state[55:70]=np.concatenate([fk[n][:3,3] for n in hand.config['track_links']])
        env.eval_grasp_states[:]=torch.as_tensor(states,device=env.device)
        np.save(a.output/'perturbed_initial_states.npy',states)
    frames=[];original=env.compute_reward
    def capture(actions):
        active=env.eval_active_mask.clone()
        original(actions)
        angle=2*torch.asin(torch.norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))
        row=dict(active=active,slider=env.obj_dof_pos[:,0].clone(),
            drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1),rotation=angle,
            stage_event=env.goal_achieved_step.clone(),fall=env.debug_reset_cause_fall.clone(),
            invalid=env.debug_reset_cause_invalid.clone(),q=env.hand_dof_pos.clone(),
            target=env.cur_targets[:,:20].clone(),policy_action=env.actions.clone(),
            reward=env.rew_buf.clone(),
            goal=env.goal_obj_dof_pos[:,0].clone(),contact=env.contact_info.clone())
        frames.append({k:v.detach().cpu().numpy() for k,v in row.items()})
    env.compute_reward=capture
    if a.video_all_envs:
        from isaacgym import gymapi
        camera_frame=env.get_camera_frame
        def grid_frame(env_id=0):
            first=camera_frame(0)
            images=[first]
            # camera_frame has already fetched and rendered all camera sensors.
            for i in range(1,env.num_envs):
                camera=env.cam_handle_list[i]
                if torch.is_tensor(camera):camera=int(camera.item())
                raw=env.gym.get_camera_image(env.sim,env.envs[i],camera,gymapi.IMAGE_COLOR)
                images.append(np.asarray(raw).reshape(384,512,-1)[:,:,:3])
            columns=min(3,len(images));rows=(len(images)+columns-1)//columns
            images.extend([np.zeros_like(first)]*(rows*columns-len(images)))
            return np.concatenate([np.concatenate(images[j*columns:(j+1)*columns],axis=1) for j in range(rows)],axis=0)
        env.get_camera_frame=grid_frame
    writer=None
    if a.video:
        import imageio.v2 as imageio
        writer=imageio.get_writer(a.output/'policy.mp4',fps=30)
    try:stats=run_grasp_evaluation_loop(player,env,deterministic=not a.stochastic,progress_interval_sec=10,video_writer=writer,
        use_student_encoder=a.student_artifact is not None)
    finally:
        if writer:writer.close()
    trace={k:np.stack([row[k] for row in frames]) for k in frames[0]}
    np.savez_compressed(a.output/'trace.npz',**trace)
    records=[]
    for i,cycles in enumerate(stats['consecutive_success_cycles']):
        mask=trace['active'][:,i];events=np.flatnonzero(trace['stage_event'][:,i]*mask)
        first_end=int(events[1])+1 if len(events)>=2 else int(mask.sum())
        records.append(dict(env=i,cycles=cycles,completion_reason=stats['completion_reason'][i],
            grasp_index=a.grasp_index if a.grasp_index is not None else i%env.eval_base_num_grasps,
            saved_initial_state_row=None if a.initial_states is None else rows[i],
            stage_times_seconds=(events*env.dt*env.control_freq_inv).tolist(),
            first_cycle_max_drift_m=float(trace['drift'][:first_end,i].max()),
            first_cycle_max_rotation_rad=float(trace['rotation'][:first_end,i].max()),
            rollout_max_drift_m=float(trace['drift'][mask,i].max()),
            rollout_max_rotation_rad=float(trace['rotation'][mask,i].max()),
            max_slider_m=float(trace['slider'][mask,i].max()),min_slider_m=float(trace['slider'][mask,i].min()),
            reward_sum=float(trace['reward'][mask,i].sum()),
            fall=bool(trace['fall'][mask,i].any()),invalid=bool(trace['invalid'][mask,i].any())))
    report=dict(checkpoint=str(a.checkpoint),checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        audit_source_sha256=audit_source_sha256,
        config_sha256=hashlib.sha256((a.output/'config.yaml').read_bytes()).hexdigest(),
        policy_type='student' if a.student_artifact else 'teacher',
        student_artifact=None if a.student_artifact is None else str(a.student_artifact),
        student_sha256=None if a.student_artifact is None else hashlib.sha256(a.student_artifact.read_bytes()).hexdigest(),
        seed=a.seed,task=a.task,envs=a.envs,control_dt=env.dt*env.control_freq_inv,
        deterministic=not a.stochastic,
        observation_frame_adapter_sha256=frame_adapter_sha256,
        execution_intervention=dict(thumb_joint2_tracking_limit_rad=a.thumb_tracking_limit,
                                    source_sha256=intervention_source_sha256),
        saved_initial_states=dict(path=None if a.initial_states is None else str(a.initial_states),
                                  sha256=saved_initial_state_sha256,rows=None if a.initial_states is None else rows),
        instance=a.instance,grasp_split=a.grasp_split,grasp_index=a.grasp_index,
        perturbation=dict(position_per_axis_mm=a.perturb_position_mm,joint_rad=a.perturb_joint_rad,
                          rotation_vector_per_axis_degrees=a.perturb_rotation_deg),
        successful_trials=sum(r['cycles']>=1 for r in records),
        strict_first_cycle_trials=sum(r['cycles']>=1 and r['first_cycle_max_drift_m']<.01 and
            r['first_cycle_max_rotation_rad']<.25 for r in records),
        stable_full_rollout_trials=sum(r['cycles']>=1 and r['rollout_max_drift_m']<.01 and
            r['rollout_max_rotation_rad']<.25 and r['completion_reason']=='episode_timeout' and
            not r['fall'] and not r['invalid'] for r in records),
        base_grasps=env.eval_base_num_grasps,
        scope='Explicit grasp split/index and parallel repeat counts; learned SAPG block 0; physical conditions in config.yaml',
        records=records,official_stats=stats)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['records','official_stats']}),flush=True)
    env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
