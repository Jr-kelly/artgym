"""Fixture-only material-combination check, never robot/demo assistance."""
import argparse,json
from pathlib import Path
from isaacgym import gymapi,gymtorch
import torch,numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    gym=gymapi.acquire_gym();s=gymapi.SimParams();s.dt=1/240;s.substeps=1;s.gravity=gymapi.Vec3(0,0,-9.81);s.up_axis=gymapi.UP_AXIS_Z;s.physx.num_position_iterations=8;s.physx.num_velocity_iterations=2
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,s);assert sim
    plane=gymapi.PlaneParams();plane.normal=gymapi.Vec3(0,0,1);plane.static_friction=.8;plane.dynamic_friction=.8;gym.add_ground(sim,plane)
    opt=gymapi.AssetOptions();opt.disable_gravity=False;asset=gym.create_box(sim,.20,.20,.03,opt)
    env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,1),1);pose=gymapi.Transform();pose.p.z=.016
    actor=gym.create_actor(env,asset,pose,'fixture',0,0);bodies=gym.get_actor_rigid_body_properties(env,actor);bodies[0].mass=.064;gym.set_actor_rigid_body_properties(env,actor,bodies,True)
    shapes=gym.get_actor_rigid_shape_properties(env,actor)
    for shape in shapes:shape.friction=2.4;shape.restitution=0
    gym.set_actor_rigid_shape_properties(env,actor,shapes);gym.prepare_sim(sim)
    applied=torch.zeros((1,3),dtype=torch.float32);samples=[]
    try:
        for force in [0.,.7,1.1,2.]:
            velocities=[]
            for i in range(240):
                previous=float(gym.get_actor_rigid_body_states(env,actor,gymapi.STATE_ALL)['vel']['linear'][0]['x'])
                applied[0,0]=force;gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(applied),None,gymapi.ENV_SPACE)
                gym.simulate(sim);gym.fetch_results(sim,True)
                state=gym.get_actor_rigid_body_states(env,actor,gymapi.STATE_ALL);v=float(state['vel']['linear'][0]['x']);velocities.append(v)
                if i>=120:samples.append(dict(force_N=force,velocity_m_s=v,friction_N=force-.064*(v-previous)*240))
            print(json.dumps(dict(force_N=force,velocity_final_m_s=velocities[-1])),flush=True)
        by={force:float(np.mean([x['friction_N'] for x in samples if x['force_N']==force])) for force in [0.,.7,1.1,2.]}
        result=dict(body_mass_kg=.064,expected_normal_N=.064*9.81,body_friction=2.4,ground_static_dynamic_friction=.8,measured_balancing_friction_N=by,measured_effective_mu_at_2N=by[2.]/(.064*9.81),predictions_mu={'average':1.6,'multiply':1.92,'min':.8,'max':2.4},scope='Known applied COM horizontal force minus measured mass*acceleration in broad stable fixture; material combine semantics only. No fixture in robotdemo, no realmaterial claim.')
        (a.output/'calibration.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    finally:gym.destroy_sim(sim)
if __name__=='__main__':main()
