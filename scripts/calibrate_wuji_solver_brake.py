"""Known-force fixed-rail fixture for a passive zero-velocity drive brake.

Only this fixture fixes the knife body and widens its rail limits. Formal
continuous demos keep their original free knife,50mm rail and all hand physics.
"""
from isaacgym import gymapi,gymtorch
import torch
import argparse,json,pathlib,xml.etree.ElementTree as ET
import numpy as np

def run(root,hz,external,cap,damping):
    gym=gymapi.acquire_gym();p=gymapi.SimParams();p.dt=1/hz;p.substeps=1;p.gravity=gymapi.Vec3(0,0,0);p.use_gpu_pipeline=False;p.physx.use_gpu=True;p.physx.solver_type=1;p.physx.num_position_iterations=8;p.physx.num_velocity_iterations=2;p.physx.contact_offset=.001;p.physx.rest_offset=0
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,p);assert sim
    env=gym.create_env(sim,gymapi.Vec3(-1,-1,-1),gymapi.Vec3(1,1,1),1);opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.override_com=False;opt.override_inertia=False
    asset=gym.load_asset(sim,str(root),'fixture.urdf',opt);actor=gym.create_actor(env,asset,gymapi.Transform(),'fixed_rail',0,0)
    shapes=gym.get_actor_rigid_shape_properties(env,actor)
    for shape in shapes:shape.filter=1;shape.friction=0
    gym.set_actor_rigid_shape_properties(env,actor,shapes)
    props=gym.get_actor_dof_properties(env,actor);props['driveMode'][:]=gymapi.DOF_MODE_VEL if cap else gymapi.DOF_MODE_EFFORT;props['stiffness'][:]=0;props['damping'][:]=damping;props['effort'][:]=cap;props['friction'][:]=0;props['armature'][:]=.001;gym.set_actor_dof_properties(env,actor,props)
    state=np.zeros(1,dtype=gymapi.DofState.dtype);gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL);gym.set_actor_dof_velocity_targets(env,actor,np.zeros(1,dtype=np.float32));gym.enable_actor_dof_force_sensors(env,actor);gym.prepare_sim(sim);forces=torch.zeros((2,3));forces[1,2]=external;samples=[];oldq=0.;oldv=0.;work=0.
    for k in range(int(.20*hz)):
        gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(forces),None,gymapi.ENV_SPACE);gym.simulate(sim);gym.fetch_results(sim,True);z=gym.get_actor_dof_states(env,actor,gymapi.STATE_ALL);q=float(z['pos'][0]);v=float(z['vel'][0]);samples.append({'t':(k+1)/hz,'q':q,'v':v,'acceleration':(v-oldv)*hz,'dq':q-oldq,'dof_force_sensor_N':float(gym.get_actor_dof_forces(env,actor)[0])});oldq=q;oldv=v
    mass=gym.get_actor_rigid_body_properties(env,actor)[1].mass;gym.destroy_sim(sim)
    return {'hz':hz,'external_known_force_N':external,'drive_force_cap_N':cap,'drive_damping_Ns_m':damping,'native_slider_mass_kg':mass,'armature':.001,'samples':samples}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source=pathlib.Path('assets/objects/knife_wuji_real_size_20261002/000');tree=ET.parse(source/'mobility.urdf');joint=tree.find('joint');joint.find('limit').set('lower','-100');joint.find('limit').set('upper','100');joint.find('limit').set('velocity','100')
    for node in tree.findall('.//mesh'):node.set('filename',str((source/node.get('filename')).resolve()))
    tree.write(a.output/'fixture.urdf',encoding='utf-8',xml_declaration=True)
    rows=[run(a.output.resolve(),240,.2,0,0),run(a.output.resolve(),240,.2,.5,250),run(a.output.resolve(),240,.75,.5,250),run(a.output.resolve(),240,-.75,.5,250),run(a.output.resolve(),480,.75,.5,250)]
    effective_mass=.2/np.mean([x['acceleration'] for x in rows[0]['samples'][:3]]);summ=[]
    for r in rows:
        brake=[r['external_known_force_N']-effective_mass*x['acceleration'] for x in r['samples']]
        work=sum(-f*x['dq'] for f,x in zip(brake,r['samples']));r['derived_brake_on_slider_N']=(-np.array(brake)).tolist();r['brake_work_J']=work;r['effective_mass_from_free_acceleration_kg']=effective_mass;summ.append({k:v for k,v in r.items() if k not in ['samples','derived_brake_on_slider_N']});summ[-1]['last_velocity_m_s']=r['samples'][-1]['v'];summ[-1]['last_brake_on_slider_N']=-brake[-1]
    (a.output/'calibration.json').write_text(json.dumps(rows,indent=2));(a.output/'summary.json').write_text(json.dumps(summ,indent=2));print(json.dumps(summ))
if __name__=='__main__':main()
