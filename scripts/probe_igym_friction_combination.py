"""Five flat-block material calibration cases, not a knife manipulation demo.

The unpopulated nativecontact friction field cannot establish mixing behavior.
Measure onset of sliding under a slow horizontal COM force ramp, with original
G2 experiment PhysX settings. Geometry is wide along force to avoid tipping.
"""
import argparse, json, time
from pathlib import Path
from isaacgym import gymapi, gymtorch
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    pairs=[(.8,.8),(.8,2.4),(2.4,.8),(2.4,2.4),(.65,3.4)];n=len(pairs)
    gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2;sp.physx.contact_offset=.001;sp.physx.rest_offset=0;sp.physx.max_depenetration_velocity=1.;sp.physx.num_threads=4
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);assert sim
    opt=gymapi.AssetOptions();opt.fix_base_link=True;table_asset=gym.create_box(sim,.6,.4,.05,opt);opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False;block_asset=gym.create_box(sim,.135,.016,.012,opt);envs=[];bodies=[]
    for i,(first,second) in enumerate(pairs):
        env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,2),3);table_t=gymapi.Transform();table_t.p=gymapi.Vec3(0,0,.725);table=gym.create_actor(env,table_asset,table_t,'table',i,0);block_t=gymapi.Transform();block_t.p=gymapi.Vec3(0,0,.7561);block=gym.create_actor(env,block_asset,block_t,'block',i,0)
        for actor,friction in [(table,first),(block,second)]:
            props=gym.get_actor_rigid_shape_properties(env,actor)
            for shape in props:shape.friction=friction
            gym.set_actor_rigid_shape_properties(env,actor,props)
        props=gym.get_actor_rigid_body_properties(env,block);props[0].mass=.035;gym.set_actor_rigid_body_properties(env,block,props,True);envs.append(env);bodies.append(block)
    gym.prepare_sim(sim);rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim)).view(n,2,13);contact=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim)).view(n,2,3);forces=torch.zeros((n,2,3));frames=[];start=time.monotonic()
    try:
        for step in range(16*240):
            t=step/240;ratio=np.clip((t-2)/4,0,3);forces[:,1,0]=float(.035*9.81*ratio)
            gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(forces.view(-1,3)),None,gymapi.ENV_SPACE);gym.simulate(sim);gym.fetch_results(sim,True)
            if step%8==7:
                gym.refresh_rigid_body_state_tensor(sim);gym.refresh_net_contact_force_tensor(sim);frames.append(dict(time=(step+1)/240,ratio=ratio,state=rb[:,1].numpy().copy(),contact=contact[:,1].numpy().copy()))
        times=np.array([r['time'] for r in frames]);ratios=np.array([r['ratio'] for r in frames]);state=np.array([r['state'] for r in frames]);contacts=np.array([r['contact'] for r in frames]);rows=[]
        for i,(first,second) in enumerate(pairs):
            candidate=(state[:,i,7]>.01)&(times>2);starts=[j for j in range(len(times)-2) if candidate[j:j+3].all()];index=starts[0] if starts else None
            rows.append(dict(table_friction=first,block_friction=second,onset_time_s=float(times[index]) if index is not None else None,force_over_mg_at_sliding_onset=float(ratios[index]) if index is not None else None,predicted_average=(first+second)/2,predicted_minimum=min(first,second),predicted_maximum=max(first,second),settled_normal_contact_N=float(contacts[(times>1)&(times<2),i,2].mean()),mass_kg=.035))
        np.savez_compressed(a.output/'trace.npz',time=times,force_over_mg=ratios,body_state=state,contact=contacts)
        result=dict(rows=rows,wall_seconds=time.monotonic()-start,physics=dict(hz=240,solver_iterations=[8,2],contact_offset_m=.001,rest_offset_m=0,gravity=9.81),scope='Engine material mixing/sliding-onset diagnostic with a wide flat cuboid andslowforce ramp; not realfriction measurement, knife operation, model learning or exactstaticfriction calibration. No robottransport.')
        (a.output/'report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    finally:gym.destroy_sim(sim)


if __name__=='__main__':main()
