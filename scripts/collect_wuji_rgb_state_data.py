"""Collect aligned camera frames and supervised state labels under a frozen teacher.

Images are a prospective extra sensor modality. They do not feed this rollout's
teacher. Segmentation measures visibility only and must not be an inference
input. This is simulation sensor preparation, not a trained vision policy.
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
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.wuji_physical_state_encoder import encode_target,SCALES
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=int,choices=[2,5],required=True)
    p.add_argument('--runtime-check',action='store_true')
    args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    original=wuji_goal_common.make_player;refs={};records=[];chunks=[]
    selected=[0,100,200] if args.runtime_check else [b+i for b in [0,100,200] for i in range(30)]
    (args.output/'source-collector.py').write_bytes(Path(__file__).read_bytes())
    def make_player(cfg,checkpoint):
        cfg.graphics_device_id=0;cfg.task.env.enableCameraSensors=True
        env,player=original(cfg,checkpoint)
        assert env.graphics_device_id==0 and env.num_envs==len(selected)
        model=player.model.eval();refs.update(model=model,before=tensor_digest(model.state_dict()))
        cameras=[];center=np.array([0.,-.085,.525]);offset=np.array([0.,.25,.12])
        for handle,obj in zip(env.envs,env.object_handles):
            names=env.gym.get_actor_rigid_body_names(handle,obj);assert names==['link_0','link_1']
            for body in range(2):env.gym.set_rigid_body_segmentation_id(handle,obj,body,body+101)
            props=gymapi.CameraProperties();props.width=props.height=320;props.horizontal_fov=45.
            camera=env.gym.create_camera_sensor(handle,props);assert camera>=0
            env.gym.set_camera_location(camera,handle,gymapi.Vec3(*(center+offset)),gymapi.Vec3(*center))
            cameras.append(camera)
        action=player.get_action;counter=[0]
        def flush():
            if not records:return
            path=args.output/f'frames-{len(chunks):04d}.npz'
            np.savez_compressed(path,**{k:np.stack([x[k] for x in records]) for k in records[0]})
            chunks.append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),frames=len(records)))
            records.clear()
        def observe(obs,is_deterministic=False,**kwargs):
            assert is_deterministic
            step=counter[0]
            # At t=0 the renderer has not yet received a physical update after
            # reset. Collect t>=1 only; t is the pre-action state for u_t.
            if step>=1 and (args.runtime_check or step%3==1):
                env.gym.fetch_results(env.sim,True);env.gym.step_graphics(env.sim);env.gym.render_all_camera_sensors(env.sim)
                images=[];visibility=[]
                for handle,camera in zip(env.envs,cameras):
                    rgb=np.asarray(env.gym.get_camera_image(env.sim,handle,camera,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(320,320,4)[...,:3].copy()
                    segmentation=np.asarray(env.gym.get_camera_image(env.sim,handle,camera,gymapi.IMAGE_SEGMENTATION)).reshape(320,320)
                    assert np.max(rgb)>0,'Black frame is invalid, not occlusion'
                    images.append(rgb);visibility.append([int((segmentation==body).sum()) for body in [101,102]])
                with torch.no_grad():
                    initial=obs[:,:55].clone();truth=encode_target(initial,obs[:,111:132])*obs.new_tensor(SCALES)
                records.append(dict(step=np.int32(step),rgb=np.stack(images),known_initial=initial.cpu().numpy(),
                    proprio=obs[:,55:95].cpu().numpy().copy(),goal=obs[:,95:96].cpu().numpy().copy(),
                    target=truth.cpu().numpy(),active=env.eval_active_mask.cpu().numpy().copy(),
                    visibility=np.asarray(visibility,dtype=np.int32)))
                if step in [1,151,301,451]:
                    imageio.imwrite(args.output/f'camera-step{step:04d}-no-text.png',np.concatenate(images[:3],axis=1))
                if len(records)>=20:flush()
                atomic_json(args.output/'collection-status.json',dict(status='collecting',step=step,sim_envs=env.num_envs,complete_chunks=chunks,heartbeat=now()))
            counter[0]+=1
            return action(obs,is_deterministic=is_deterministic,**kwargs)
        player.get_action=observe;refs['flush']=flush
        return env,player
    wuji_goal_common.make_player=make_player;argv=sys.argv
    try:
        sys.argv=[argv[0],'--checkpoint',str(ROOT/TEACHER),'--output',str(args.output),
            '--task','wuji_acquisition_bridge3_hemisphere','--hand','wuji_paper_official_actuator',
            '--object','knife_wuji_bridge3_20260922','--initial-states',str(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
            '--initial-state-rows']+list(map(str,selected))+['--stage-seconds',str(args.seconds),'--seed','20261060']
        from scripts.audit_wuji_timed_commands import main as evaluate
        evaluate();refs['flush']()
        assert tensor_digest(refs['model'].state_dict())==refs['before']
        frames=sum(c['frames'] for c in chunks);assert frames==(599 if args.runtime_check else 200)
        report=json.loads((args.output/'report.json').read_text())
        atomic_json(args.output/'collection-status.json',dict(status='completed',finished=now(),chunks=chunks,frames=frames,images=frames*len(selected),
            selected_initial_rows=selected,training_rows=[i for i in selected if i%100<20],validation_rows=[i for i in selected if i%100>=20],
            teacher_sha256=hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest(),teacher_unchanged=True,
            physics_transitions=600*len(selected),reported_strict_success=report['stable_full_all_endpoints'],
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope=__doc__,
            clock_seconds=args.seconds,camera=dict(center=[0.,-.085,.525],offset=[0.,.25,.12],resolution=[320,320],horizontal_fov=45),
            state_target='body_translation3_m,body_rotation_vector3_rad,slider_position_m,slider_velocity_mps',
            synchronization='RGB and current observation sampled after fetch/step_graphics and before action; t0 excluded',
            segmentation_use='Visibility diagnostics only, excluded from prospective actor inputs',
            rendering_changes_physics=False,trained_vision_policy=False))
    except BaseException as exc:
        atomic_json(args.output/'failure.json',dict(error=repr(exc),time=now(),chunks=chunks));raise
    finally:
        sys.argv=argv;wuji_goal_common.make_player=original


if __name__=='__main__':main()
