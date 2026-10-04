"""Known signed guide effort calibration of collisionless serial carrier.

Diagnostic modified device only. Carrier Newton balance includes measured
world acceleration, gravity and the applied spring force. Candidate generalized
armature correction is separately validated, rather than presumed physical.
"""
from isaacgym import gymapi,gymtorch
import argparse,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation


def run(path,moving,armature):
    par=json.loads((path.parent/'parameters.json').read_text())['serial_load_cell']
    hz=960;gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/hz
    sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81)
    sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1
    sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);assert sim
    env=gym.create_env(sim,gymapi.Vec3(-1,-1,-1),gymapi.Vec3(1,1,1),1)
    opt=gymapi.AssetOptions();opt.fix_base_link=not moving;opt.disable_gravity=False
    opt.override_com=False;opt.override_inertia=False
    asset=gym.load_asset(sim,str(path.resolve().parent),path.name,opt)
    pose=gymapi.Transform();pose.r=gymapi.Quat(*Rotation.from_euler('y',45 if moving else 90,degrees=True).as_quat())
    actor=gym.create_actor(env,asset,pose,'guide_fixture',0,0)
    forprops=gym.get_actor_rigid_shape_properties(env,actor)
    for s in forprops:s.filter=1;s.friction=0.
    gym.set_actor_rigid_shape_properties(env,actor,forprops)
    names=gym.get_actor_dof_names(env,actor);bodies=gym.get_actor_rigid_body_names(env,actor)
    guide=names.index('slider');cell=names.index('serial_load_cell')
    carrier=bodies.index('load_cell_carrier');cap=bodies.index('link_1')
    props=gym.get_actor_dof_properties(env,actor)
    props['driveMode'][:]=gymapi.DOF_MODE_EFFORT;props['damping'][:]=0
    props['stiffness'][:]=0;props['friction'][:]=0;props['armature'][:]=0
    props['armature'][guide]=armature;props['effort'][:]=10
    props['driveMode'][guide]=gymapi.DOF_MODE_VEL;props['damping'][guide]=250;props['effort'][guide]=.2
    gym.set_actor_dof_properties(env,actor,props)
    gym.set_actor_dof_velocity_targets(env,actor,np.zeros(2,np.float32))
    state=np.zeros(2,dtype=gymapi.DofState.dtype)
    state['pos'][guide]=(props['lower'][guide]+props['upper'][guide])/2
    gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL);gym.prepare_sim(sim)
    d=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim))
    rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim))
    effort=torch.zeros(2);force=torch.zeros((len(bodies),3));torque=torch.zeros_like(force)
    rows=[]
    for step in range(hz//2):
        gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim)
        axis=Rotation.from_quat(rb[0,3:7].numpy()).apply([0,0,1])
        oldvel=rb[carrier,7:10].numpy().copy();oldqv=float(d[guide,1])
        known=.04*np.cos(2*np.pi*40*step/hz)
        capforce=.03*np.cos(2*np.pi*40*step/hz)
        spring=-par['spring_N_per_m']*float(d[cell,0])-par['damper_N_s_per_m']*float(d[cell,1])
        effort[guide]=known;effort[cell]=spring;force[:]=0;torque[:]=0
        force[cap]=torch.tensor(axis*capforce,dtype=torch.float32)
        if moving:
            force[0,0]=.002*np.sin(step/hz*20);torque[0,1]=.0000002*np.sin(step/hz*15)
        gym.set_dof_actuation_force_tensor(sim,gymtorch.unwrap_tensor(effort))
        gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(force),gymtorch.unwrap_tensor(torque),gymapi.ENV_SPACE)
        gym.simulate(sim);gym.fetch_results(sim,True)
        gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim)
        axis=Rotation.from_quat(rb[0,3:7].numpy()).apply([0,0,1])
        acc=(rb[carrier,7:10].numpy()-oldvel)*hz
        raw=par['carrier_mass_kg']*float(acc@axis)-par['carrier_mass_kg']*float(np.array([0,0,-9.81])@axis)+spring
        qdd=(float(d[guide,1])-oldqv)*hz
        corrected=raw+armature*qdd
        safe=props['lower'][guide]+.001<float(d[guide,0])<props['upper'][guide]-.001 and abs(float(d[cell,0]))<.0019
        expected=known+float(np.clip(-250*float(d[guide,1]),-.2,.2))
        rows.append([step/hz,expected,raw,corrected,qdd,float(d[guide,0]),float(d[cell,0]),float(safe)])
    gym.destroy_sim(sim);z=np.array(rows)
    mask=z[:,7]>0
    rawerr=abs(z[:,2]-z[:,1]);err=abs(z[:,3]-z[:,1])
    correction_needed=bool(err.max()<rawerr.max())
    best=err if correction_needed else rawerr
    return z,dict(moving_base=moving,configured_guide_armature=armature,
        raw_max_residual_N=float(rawerr.max()),armature_corrected_max_residual_N=float(err.max()),
        correction_needed=correction_needed,no_endstop=bool(mask.all()),passed=bool(mask.all() and best.max()<.01),
        max_validated_residual_N=float(best.max()))


def main():
    p=argparse.ArgumentParser();p.add_argument('--asset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);rows=[]
    for name,moving,armature in [('fixed-zero',False,0.),('fixed-armature',False,.001),('moving-armature',True,.001)]:
        z,r=run(a.asset,moving,armature);rows.append(dict(name=name,**r))
        np.savez_compressed(a.output/(name+'.npz'),samples=z,
            columns=['time_s','known_guide_effort_N','carrier_newton_axial_N','armature_corrected_N','guide_qdd_m_s2','guide_q_m','cell_q_m','valid'])
    result=dict(scope=__doc__,rows=rows,passed=all(r['passed'] for r in rows),
                inference='If passed: modifieddevice total generalized guidejoint reaction. Fixture compares known imposed effort plus implicit zero-velocity drive reconstructed from poststepvelocity, calibrated250 damping/.2 saturation and zero fixturefriction. This is separate from the operational unknown drive/friction decomposition; never substitute capacity for actual force.')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True);assert result['passed']


if __name__=='__main__':main()
