"""Plan a continuous loaded wrist roll from this route's actual held state."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def plan(source,degrees,duration=6.,free_position=False,lift_m=0.,start_delay=.5,minimum_margin=.025):
 z=np.load(source/'takeover.npz');k=G2Kinematics();O=transform(z['object_state'][:3],z['object_state'][3:7]);actualW=k.forward(z['robot_q'][:7]);L=np.linalg.inv(O)@actualW
 # Start at the previously issued arm reference, without unloading the PD.
 W0=k.forward(z['issued_target'][:7]);plannedO=W0@np.linalg.inv(L);q=z['issued_target'][:7].astype(float);rows=[];errors=[]
 for t in np.arange(0,duration+1/60,1/30):
  u=smooth((t-start_delay)/(duration-2.));angle=np.deg2rad(degrees)*u;D=transform(quaternion=Rotation.from_euler('z',angle).as_quat());goal=plannedO@D@L;goal[2,3]+=lift_m*u
  if free_position:
   from scipy.optimize import least_squares
   # Coordinated arm roll: orient at the wrist while permitting a modest
   # reachable translation. Avoid insisting on an unreachable fixed root.
   goal[:3,3]=W0[:3,3]+np.array([0,0,lift_m*u])
   seed=q.copy()
   def residual(x):
    F=k.forward(x)
    return np.r_[Rotation.from_matrix(goal[:3,:3].T@F[:3,:3]).as_rotvec()*2,(F[:3,3]-goal[:3,3])*.5,(x-seed)*.008]
   lo=np.maximum(k.lower+minimum_margin,seed-.12);hi=np.minimum(k.upper-minimum_margin,seed+.12)
   fit=least_squares(residual,np.clip(seed,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=120);q=fit.x;F=k.forward(q)
   estimatedO=F@np.linalg.inv(L)
   from scripts.g2_knife_geometry import KnifeGeometry
   if t==0:G=KnifeGeometry(Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));V=np.concatenate([p['vertices'] for p in G.collision_parts(float(z['slider_q']))])
   e=dict(position_m=float(np.linalg.norm(F[:3,3]-goal[:3,3])),rotation_rad=float(Rotation.from_matrix(goal[:3,:3].T@F[:3,:3]).magnitude()),max_joint_step_rad=float(abs(q-seed).max()),joint_margin_rad=float(np.minimum(q-k.lower,k.upper-q).min()),planned_whole_clearance_m=float((V@estimatedO[:3,:3].T+estimatedO[:3,3])[:,2].min()-.75))
  else:q,e=k.solve_near(goal,q,max_step=.12,minimum_margin=minimum_margin)
  rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=z['issued_target'][7:].tolist()));errors.append(e)
 return dict(rows=rows,source=str(source),degrees=degrees,duration_s=duration,lift_m=lift_m,start_delay_s=start_delay,minimum_margin_rad=minimum_margin,wrist_in_actual_knife=L.tolist(),ik=errors,scope='Motorreferences only; retained actual loaded hand; recorded devinit is not final continuous result')

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--degrees',type=float,default=150);p.add_argument('--duration',type=float,default=6);p.add_argument('--free-position',action='store_true');p.add_argument('--lift-m',type=float,default=0);p.add_argument('--start-delay',type=float,default=.5);p.add_argument('--minimum-margin',type=float,default=.025);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 s=plan(a.source,a.degrees,a.duration,a.free_position,a.lift_m,a.start_delay,a.minimum_margin);(a.output/'roll.json').write_text(json.dumps(s,indent=2));report={key:max(r[key] for r in s['ik']) for key in ['position_m','rotation_rad','max_joint_step_rad']};report['min_joint_margin_rad']=min(r['joint_margin_rad'] for r in s['ik']);report['free_position']=a.free_position
 if a.free_position:report['planned_min_whole_clearance_m']=min(r['planned_whole_clearance_m'] for r in s['ik'])
 (a.output/'planning.json').write_text(json.dumps(report,indent=2));print(report)
 record('direct_roll_geometry_planned',[str(a.output/'roll.json'),str(a.output/'planning.json')],config=dict(degrees=a.degrees,**report),next_step='Execute loaded native roll only if continuous arm feasible; actualcontacts decide supporttransfer')
if __name__=='__main__':main()
