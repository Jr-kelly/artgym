"""Low-speed known-load fixture verifies selected capacity profiles and signs.
Fixed body/external force only here; free demos never use these fixtures.
"""
from isaacgym import gymapi,gymtorch
import torch
import json,argparse
from pathlib import Path
import numpy as np
from scripts.wuji_newknife_resistance import capacity

def run(asset,profile,direction):
 g=gymapi.acquire_gym();p=gymapi.SimParams();p.dt=1/240;p.gravity=gymapi.Vec3(0,0,0);p.physx.use_gpu=True;p.physx.solver_type=1;p.physx.num_position_iterations=8;p.physx.num_velocity_iterations=2;p.physx.contact_offset=.001;p.physx.rest_offset=0
 sim=g.create_sim(0,-1,gymapi.SIM_PHYSX,p);e=g.create_env(sim,gymapi.Vec3(-1,-1,-1),gymapi.Vec3(1,1,1),1);o=gymapi.AssetOptions();o.fix_base_link=True;o.override_com=False;o.override_inertia=False;obj=g.load_asset(sim,str(asset.resolve().parent),asset.name,o);actor=g.create_actor(e,obj,gymapi.Transform(),'fixture',0,0)
 shapes=g.get_actor_rigid_shape_properties(e,actor)
 for s in shapes:s.filter=1;s.friction=0
 g.set_actor_rigid_shape_properties(e,actor,shapes);d=g.get_actor_dof_properties(e,actor);d['driveMode'][:]=gymapi.DOF_MODE_VEL;d['stiffness'][:]=0;d['damping'][:]=25000;d['effort'][:]=capacity(profile,0,0);d['friction'][:]=0;d['armature'][:]=.001;g.set_actor_dof_properties(e,actor,d);g.set_actor_dof_velocity_targets(e,actor,np.zeros(1,np.float32))
 q0=0 if direction>0 else .035;ds=np.zeros(1,dtype=gymapi.DofState.dtype);ds['pos'][0]=q0;g.set_actor_dof_states(e,actor,ds,gymapi.STATE_ALL);g.prepare_sim(sim);f=torch.zeros((2,3));rows=[];q=q0;velocity=0
 for k in range(144 if profile['kind']=='constant' else 48):
  t=k/240;cap=capacity(profile,q,velocity);d['effort'][:]=cap;g.set_actor_dof_properties(e,actor,d)
  force=(.7365 if profile['kind']=='constant' else (.825 if t<.020 else 0.))*direction
  f[1,2]=force;g.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(f),None,gymapi.ENV_SPACE);g.simulate(sim);g.fetch_results(sim,True);z=g.get_actor_dof_states(e,actor,gymapi.STATE_ALL);nq=float(z['pos'][0]);nv=(nq-q)*240
  rows.append(dict(t=(k+1)/240,q_rel_m=nq,reported_velocity_m_s=float(z['vel'][0]),position_difference_velocity_m_s=nv,capacity_N=cap,known_force_N=force,inferred_opposing_force_N=force-.012*(nv-velocity)*240,away_from_endstops=(-.008<nq<.053)));q=nq;velocity=nv
 g.destroy_sim(sim);return dict(kind=profile['kind'],direction=direction,initial_q_m=q0,rows=rows)
def main():
 p=argparse.ArgumentParser();p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);trials=[]
 for kind in ['variable']:
  profile=json.loads(Path(f'research/newknife-20261005/resistance-{kind}.json').read_text())
  for direction in [1,-1]:
   trials.append(run(a.asset,profile,direction));(a.output/'raw.json').write_text(json.dumps(trials,indent=2))
 summary=[]
 for r in trials:
  rows=r['rows'];valid=[x for x in rows[3:] if x['away_from_endstops'] and abs(x['position_difference_velocity_m_s'])>.003]
  summary.append(dict(kind=r['kind'],direction=r['direction'],displacement_m=rows[-1]['q_rel_m']-r['initial_q_m'],capacity_range_N=[min(x['capacity_N'] for x in rows),max(x['capacity_N'] for x in rows)],endstop_avoided=all(x['away_from_endstops'] for x in rows),inferred_force_minus_capacity_abs_median_N=float(np.median([abs(abs(x['inferred_opposing_force_N'])-x['capacity_N']) for x in valid])) if valid else None))
 (a.output/'summary.json').write_text(json.dumps(dict(scope='Known force response of isolated fixture; inertia inference only while moving away from endstops; variable curve assumed not measured; no robotB/C',trials=summary),indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
