"""Native imported G2/Wuji pose comparison for four fixed cache representatives.

Pre-simulation state writes are diagnostic initialization only. This does not
measure operation success, force, or continuous pickup.
"""
import argparse,json
from pathlib import Path
from isaacgym import gymapi
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import WujiKinematics

R=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--comparison',type=Path,required=True);a=p.parse_args()
    gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.physx.use_gpu=True
    sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);assert sim
    opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.disable_gravity=False;opt.collapse_fixed_joints=False
    asset=gym.load_asset(sim,str(R/'assets/robots/g2_wuji'),'g2_wuji.urdf',opt)
    names=gym.get_asset_dof_names(asset);h=WujiKinematics();k=G2Kinematics();hand=[names.index(n) for n in h.names];arm=[names.index(n) for n in k.names]
    assert len(names)==27 and set(hand).isdisjoint(arm)
    records=[]
    for source in range(4):
        folder=a.comparison/('source%d'%source);plan=json.loads((folder/'motor-plan.json').read_text());q=np.asarray(plan['touch_q']);qa=np.asarray(json.loads((folder/'arm-seed.json').read_text()))
        env=gym.create_env(sim,gymapi.Vec3(-2,-2,0),gymapi.Vec3(2,2,3),2)
        actor=gym.create_actor(env,asset,gymapi.Transform(),'robot',source,1)
        state=np.zeros(len(names),dtype=gymapi.DofState.dtype);state['pos'][hand]=q;state['pos'][arm]=qa;gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL)
        native=gym.get_actor_rigid_body_states(env,actor,gymapi.STATE_POS);body=gym.get_actor_rigid_body_names(env,actor);w=k.forward(qa);fk=h.forward(q);errors=[]
        for n in fk:
            s=native[body.index(n)];pos=np.array([s['pose']['p'][x] for x in ['x','y','z']]);quat=np.array([s['pose']['r'][x] for x in ['x','y','z','w']]);expected=w@fk[n]
            errors.append(dict(link=n,position_error_m=float(np.linalg.norm(pos-expected[:3,3])),rotation_error_rad=float(Rotation.from_matrix(expected[:3,:3].T@Rotation.from_quat(quat).as_matrix()).magnitude())))
        records.append(dict(source=source,rows=errors,max_position_error_m=max(z['position_error_m'] for z in errors),max_rotation_error_rad=max(z['rotation_error_rad'] for z in errors)))
    result=dict(scope=__doc__,hand_indices=hand,arm_indices=arm,native_dof_names=names,gravity_enabled=True,rows=records,passed=all(z['max_position_error_m']<1e-5 and z['max_rotation_error_rad']<1e-5 for z in records))
    (a.comparison/'native-mapping-report.json').write_text(json.dumps(result,indent=2)+'\n');gym.destroy_sim(sim)
    print(json.dumps(dict(passed=result['passed'],maximum_position_error_m=max(z['max_position_error_m'] for z in records))))
    assert result['passed'],'Native imported hand mapping disagrees with FK'

if __name__=='__main__':main()
