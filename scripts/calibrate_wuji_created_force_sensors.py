"""One constructed-sensor fixture check, distinct from absent-sensor queries.

Even a valid net solver wrench does not isolate original cap contact traction
from joint/brake constraint forces. This is a backend channel calibration.
"""
from isaacgym import gymapi,gymtorch
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    gym=gymapi.acquire_gym();s=gymapi.SimParams();s.dt=1/240;s.substeps=1;s.up_axis=gymapi.UP_AXIS_Z;s.gravity=gymapi.Vec3(0,0,-9.81);s.physx.use_gpu=True;s.use_gpu_pipeline=False;s.physx.num_position_iterations=8;s.physx.num_velocity_iterations=2;s.physx.contact_collection=gymapi.ContactCollection(2)
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,s);assert sim
    plane=gymapi.PlaneParams();plane.normal=gymapi.Vec3(0,0,1);plane.static_friction=1.;plane.dynamic_friction=1.;gym.add_ground(sim,plane)
    asset=gym.create_box(sim,.04,.04,.04,gymapi.AssetOptions());modes=[]
    for name,forward,solver in [('both',True,True),('forward-only',True,False),('solver-only',False,True)]:
        props=gymapi.ForceSensorProperties();props.enable_forward_dynamics_forces=forward;props.enable_constraint_solver_forces=solver;props.use_world_frame=True
        index=gym.create_asset_force_sensor(asset,0,gymapi.Transform(),props);modes.append(dict(name=name,index=index,forward=forward,solver=solver))
    env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,1),1);pose=gymapi.Transform();pose.p.z=.025;actor=gym.create_actor(env,asset,pose,'constructed-sensor-fixture',0,0)
    bodies=gym.get_actor_rigid_body_properties(env,actor);bodies[0].mass=.064;gym.set_actor_rigid_body_properties(env,actor,bodies,True);gym.prepare_sim(sim)
    count=gym.get_actor_force_sensor_count(env,actor)
    if count!=len(modes) or any(gym.get_actor_force_sensor(env,actor,r['index']) is None for r in modes):
        result=dict(scope=__doc__,actor_sensor_count=count,sim_sensor_count=gym.get_sim_force_sensor_count(sim),modes=modes,calibration_passed=False,
                    reason='Newasset sensorcreation didnotyield readableactor channels; do notinterpret absent sensors as zeroforce',
                    original_cap_contact_B_isolated=False,original_guide_C_isolated=False,hardware_measurement_completed=False)
        (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));gym.destroy_sim(sim);return
    descriptor=gym.acquire_force_sensor_tensor(sim);tensor=gymtorch.wrap_tensor(descriptor) if descriptor is not None else None
    net=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim));forces=torch.tensor([[.15,0,-.4]],dtype=torch.float32);rows=[];api=[]
    try:
        for step in range(480):
            gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(forces),None,gymapi.ENV_SPACE);gym.simulate(sim);gym.fetch_results(sim,True);gym.refresh_net_contact_force_tensor(sim)
            if tensor is not None:gym.refresh_force_sensor_tensor(sim)
            if step>=240:
                if tensor is not None:rows.append(tensor.numpy().copy())
                values=[]
                for mode in modes:
                    data=gym.get_actor_force_sensor(env,actor,mode['index']).get_forces();values.append([data.force.x,data.force.y,data.force.z,data.torque.x,data.torque.y,data.torque.z])
                api.append(values)
        expected=np.array([[0,0,0],[.15,0,-1.02784],[-.15,0,1.02784]])
        observed=np.asarray(api).mean(0);error=np.linalg.norm(observed[:,:3]-expected,axis=1)
        np.savez_compressed(a.output/'raw.npz',sensor_api=np.asarray(api),sensor_tensor=np.asarray(rows),expected_force_N=expected)
        result=dict(scope=__doc__,actor_sensor_count=gym.get_actor_force_sensor_count(env,actor),sim_sensor_count=gym.get_sim_force_sensor_count(sim),modes=modes,known_mass_kg=.064,known_external_world_N=[.15,0,-.4],expected_force_world_N=expected.tolist(),api_mean_world_force_N=observed[:,:3].tolist(),force_residual_norm_N=error.tolist(),calibration_passed=bool(np.max(error)<.01),net_contact_force_last_N=net[0].numpy().tolist(),sensor_tensor_present=tensor is not None,original_cap_contact_B_isolated=False,original_guide_C_isolated=False,hardware_measurement_completed=False)
        if rows:result['tensor_mean_world_force_N']=np.asarray(rows).mean(0)[:,:3].tolist()
        (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:gym.destroy_sim(sim)


if __name__=='__main__':main()
