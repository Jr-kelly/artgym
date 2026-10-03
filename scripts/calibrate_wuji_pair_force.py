"""Known box-plane load fixture only. Never used to hold the demo knife."""
from isaacgym import gymapi, gymtorch
import argparse, json, pathlib
import numpy as np
import torch
from scripts.record_wuji_support_goal import record
def run(hz,substeps,mode):
    gym=gymapi.acquire_gym();p=gymapi.SimParams();p.dt=1/hz;p.substeps=substeps;p.up_axis=gymapi.UP_AXIS_Z;p.gravity=gymapi.Vec3(0,0,-9.81);p.use_gpu_pipeline=False;p.physx.use_gpu=True;p.physx.solver_type=1;p.physx.num_position_iterations=8;p.physx.num_velocity_iterations=2;p.physx.contact_collection=gymapi.ContactCollection(mode)
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,p);assert sim
    plane=gymapi.PlaneParams();plane.normal=gymapi.Vec3(0,0,1);plane.static_friction=1.;plane.dynamic_friction=1.;gym.add_ground(sim,plane)
    env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,1),1);o=gymapi.AssetOptions();o.density=1000.;asset=gym.create_box(sim,.04,.04,.04,o);pose=gymapi.Transform();pose.p=gymapi.Vec3(0,0,.025);actor=gym.create_actor(env,asset,pose,'known_box',0,0);mass=gym.get_actor_rigid_body_properties(env,actor)[0].mass
    gym.prepare_sim(sim);rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));net=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim));forces=torch.zeros((1,3));forces[0]=torch.tensor([.15,0,-.4]);samples=[];example=None
    for k in range(int(2*hz)):
        gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(forces),None,gymapi.ENV_SPACE);gym.simulate(sim);gym.fetch_results(sim,True);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_net_contact_force_tensor(sim)
        cs=gym.get_env_rigid_contacts(env);pairvec=np.zeros(3);raw=0.;friction=0.
        for c in cs:
            if {int(c['body0']),int(c['body1'])}!={0,-1}:continue
            v=np.array([c['normal'][x] for x in ['x','y','z']]);raw+=float(c['lambda']);pairvec+=(1 if int(c['body1'])==0 else -1)*float(c['lambda'])*v
            if 'lambda_friction' in c.dtype.names:friction+=float(c['lambda_friction'])
            if example is None:example={'fields':list(c.dtype.names),'body0':int(c['body0']),'body1':int(c['body1']),'normal_world':v.tolist(),'lambda':float(c['lambda'])}
        if k>=hz:samples.append({'raw_lambda_sum':raw,'signed_pair_vector':pairvec.tolist(),'net':net[0].numpy().copy().tolist(),'velocity':rb[0,7:10].numpy().copy().tolist(),'lambda_friction_sum':friction})
    gym.destroy_sim(sim);z={k:np.asarray([x[k] for x in samples]).mean(axis=0).tolist() for k in samples[0]};return {'physics_hz':hz,'substeps':substeps,'contact_collection':mode,'mass_kg':mass,'expected_vertical_contact_N':mass*9.81+.4,'expected_horizontal_contact_N':-.15,'mean_after_1s':z,'contact_record_example':example,'last_second_samples':samples,'scope':'Calibration fixture only. External known box forces never applied to formal knife demo. Pair normal contribution and net force kept distinct; friction direction not assumed.'}
def main():
    a=argparse.ArgumentParser();a.add_argument('--output',type=pathlib.Path,required=True);args=a.parse_args();args.output.mkdir(parents=True,exist_ok=False);record('contact_pair_load_fixture_started',config={'hz':[240,480],'substeps':[1,2],'known_external_box_force_N':[.15,0,-.4]},evidence=str(args.output),next='Determine units/sign/substep scope, immediately instrument loaded demo and modify support')
    rows=[run(240,1,2),run(480,1,2),run(240,2,1),run(240,2,2)];(args.output/'calibration.json').write_text(json.dumps(rows,indent=2));record('contact_pair_load_fixture_completed',evidence=str(args.output/'calibration.json'),conclusion='Raw calibrated samples retained; interpretation must compare expected load, dt and sign before publishing Newton pressure',next='Use calibrated pair semantics in all240Hz loaded control rollouts');print(json.dumps([{k:v for k,v in r.items() if k!='last_second_samples'} for r in rows]))
if __name__=='__main__':main()
