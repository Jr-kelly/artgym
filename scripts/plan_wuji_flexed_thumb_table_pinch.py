"""One new tabletop pad-opposed grip, retaining a flexed thumb from acquisition.

Current pickup uses a near-extended thumb and subsequently reaches an endstop.
This changes the initial contact mechanism, not the proven B goal or physics.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seed-geometry',type=Path);p.add_argument('--balanced-normal-moment',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);base=Path('runs/flat-table-20261006/direct/preparation/current-C560-fresh-no-extra-ring-v743/prefix.json');spec=json.loads(base.read_text());trace=np.load('runs/flat-table-20261006/direct/development/current-C560-fresh-no-extra-ring-v743/simulation/trace.npz');q0=np.r_[trace['arm_q'][179],trace['q'][179]].astype(float);o=trace['object'][179];f=FunctionalEntryAffordance();g=f.g;k=f.kin;O=np.array(spec['physical_initial_object_world']);L0=np.linalg.inv(transform(o[:3],o[3:7]))@k.forward(q0[:7]);h0=q0[7:].copy();target=json.loads(Path('runs/flat-table-20261006/direct/preparation/fresh-safe-prefix-free-reference-v823/reference.json').read_text())['target_hand_q'];h0[16:]=target[16:];
 if a.seed_geometry:
  seed_geometry=json.loads(a.seed_geometry.read_text());L0=np.array(seed_geometry['wrist_in_knife']);h0=np.array(seed_geometry['hand_q'])
 ids=np.array(list(range(8))+list(range(16,20)));pose0=np.r_[L0[:3,3],Rotation.from_matrix(L0[:3,:3]).as_rotvec()];x0=np.r_[pose0,h0[ids]];lo=np.r_[pose0[:3]-.020,pose0[3:]-.35,g.w.lower[ids]+.035];hi=np.r_[pose0[:3]+.020,pose0[3:]+.35,g.w.upper[ids]-.035];lo[16]=.10;x0=np.clip(x0,lo+1e-6,hi-1e-6);names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_thumb_pad_link'];V={n:np.concatenate([v for v,_ in g.meshes[n]])for n in names};regions=[(np.array([.0095,-.0038,-.015]),np.array([.0095,.001,.010])),(np.array([.0095,-.0038,-.045]),np.array([.0095,.001,-.020])),(np.array([-.0095,-.0038,-.030]),np.array([-.0095,.001,-.010]))];begin=time.monotonic();best=[float('inf'),x0.copy()];calls=[0]
 record('flexed_thumb_table_pinch_geometry_started_v864',[str(base)],dict(question='Can initialpad-sideopposition with thumbjoint3positive be tableclear and retain existingindex/middle bearing regions? Yes: genuinefreshpickup/lift, thenitsownflip and original773B-range; no: fixexplicitgeometry, no oldpressure/followerloop.',scope=__doc__,B_target='Original773 proven fullB entry remains prior; discarded863pivotcap goal isnot reused'),next_step='Oneboundedinitialgrip solve, no seed/grasp pool; ownactualpickup beforeany continuation')
 def decode(x):
  L=transform(x[:3],Rotation.from_rotvec(x[3:6]).as_quat());h=h0.copy();h[ids]=x[6:];return L,h,g.w.forward(h)
 def surfaces(L,F):
  result=[]
  for name,side in zip(names,[-1.,-1.,1.]):
   T=L@F[name];P=V[name]@T[:3,:3].T+T[:3,3];depth=side*P[:,0];w=np.exp((depth-depth.max())/.0002);result.append(w@P/w.sum())
  return result
 def residual(x):
  if time.monotonic()-begin>180:raise TimeoutError('Bounded onegrip geometry budget180s reached')
  L,h,F=decode(x);r=[]
  points=surfaces(L,F)
  for point,(low,high) in zip(points,regions):r.extend((point-np.clip(point,low,high))*700)
  if a.balanced_normal_moment:
   # Original .7/.7/1.4 normal loads have zero torque only at this centroid.
   r.extend((points[2][1:]-.5*(points[0][1:]+points[1][1:]))*1400)
  W=O@L
  for name,parts in g.meshes.items():
   T=W@F[name]
   for v,_ in parts:r.append(min(0.,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.75025))*1400)
  for digit in ['index','middle','ring','pinky','thumb']:
   for gap in g.gaps(h,L,0.,digit,frames=F):
    allowed=gap['knife_link']=='link_0' and gap['hand_link'] in names;r.append(min(0.,gap['gap_lower_bound_m']-(-.00015 if allowed else .0002))*800)
  r.extend(min(0.,gap['gap_lower_bound_m']-.0002)*800 for gap in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend((x-x0)*.015);calls[0]+=1;cost=float(np.dot(r,r))
  if cost<best[0]:best[:]=[cost,x.copy()]
  if calls[0]%250==0:print(json.dumps(dict(calls=calls[0],cost=cost,best_cost=best[0],elapsed_s=time.monotonic()-begin)),flush=True)
  return np.asarray(r)
 failure=None
 try:fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=80,diff_step=1e-5);x=fit.x
 except TimeoutError as exc:failure=str(exc);x=best[1]
 L,h,F=decode(x);points=surfaces(L,F);errors=[float(np.linalg.norm(point-np.clip(point,low,high)))for point,(low,high)in zip(points,regions)];W=O@L;floor=min(float((v@(W@F[name])[:3,:3].T+(W@F[name])[:3,3])[:,2].min()-.75)for name,parts in g.meshes.items()for v,_ in parts);H=f.H.inspect(h);arm,ik=k.solve_near(W,q0[:7],max_step=.6,minimum_margin=.035);moment_error=float(np.linalg.norm(points[2][1:]-.5*(points[0][1:]+points[1][1:]))) if a.balanced_normal_moment else 0.;eligible=moment_error<.0005 and floor>.00015 and max(errors)<.0005 and not H and ik['position_m']<.0005 and ik['rotation_rad']<.003;result=dict(balanced_normal_moment=a.balanced_normal_moment,normal_load_centroid_error_m=moment_error,wrist_in_knife=L.tolist(),hand_q=h.tolist(),arm_q=arm.tolist(),arm_IK=ik,contacts=[dict(link=n,point_knife_m=v.tolist(),region_low=low.tolist(),region_high=high.tolist(),error_m=e)for n,v,(low,high),e in zip(names,points,regions,errors)],table_clearance_m=floor,self=H,geometry_permits_native=eligible,elapsed_s=time.monotonic()-begin,calls=calls[0],failure=failure,scope=__doc__);(a.output/'candidate.json').write_text(json.dumps(result,indent=2));(a.output/'planner.py').write_text(Path(__file__).read_text());record('flexed_thumb_table_pinch_geometry_terminal_v864',[str(a.output/'candidate.json')],dict(geometry_permits_native=eligible,table_clearance_m=floor,errors_m=errors,self=H,arm_IK=ik,thumb_q=h[16:].tolist(),failure=failure),next_step='Ifclear geometrically prepareopenapproach/newpadpreload andactualfreshpickup; ifblocked exactcontact/tablefailure decides');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
