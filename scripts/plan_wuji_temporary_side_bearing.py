"""Temporary opposite-side pinky bearing geometry, not a material-point follower.

Free axial location on side face; original hand/knife collision and joint bounds.
Native carrying and thumb-free independence must be proven separately.
"""
import argparse,json
from pathlib import Path
from functools import lru_cache
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--digit',choices=['pinky','ring'],default='pinky');p.add_argument('--link',choices=['pad_link','link4'],default='pad_link');p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(Path(a.source)/'takeover.npz');q=z['robot_q'][7:].astype(float);g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@G2Kinematics().forward(z['robot_q'][:7]);sl=slice(8,12) if a.digit=='pinky' else slice(12,16);link='hand_r_'+a.digit+'_'+a.link;vertices=np.concatenate([v for v,_ in g.meshes[link]]);H=HandIntersection()
 @lru_cache(maxsize=8192)
 def calc(x):
  full=q.copy();full[sl]=x;F=g.w.forward(full);T=L@F[link];v=vertices@T[:3,:3].T+T[:3,3];w=np.exp(-(v[:,0]-v[:,0].min())/.0002);point=w@v/w.sum();gaps=g.gaps(full,L,float(z['slider_q']),a.digit,frames=F,certify_clearance_m=.0001)+g.self_gaps(full,a.digit,frames=F,certify_clearance_m=.0001);return point,np.array([r['gap_lower_bound_m'] for r in gaps]),full
 def cost(x):
  point,_,_=calc(tuple(x));return ((point[0]-.00955)*200)**2+(point[1]*200)**2+(max(abs(point[2])-.060,0)*200)**2+.0001*np.sum((x-q[sl])**2)
 def constraint(x):
  point,gaps,_=calc(tuple(x));return np.r_[(gaps+.00005)*1000,(.0037-abs(point[1]))*1000,(.068-abs(point[2]))*1000]
 rows=[];best=None
 for seed in [q[sl],np.array([.7,0.,1.,.7]),np.array([1.,-.2,1.2,.4]),np.array([1.3,.2,.8,.6])]:
  fit=minimize(cost,np.clip(seed,g.w.lower[sl]+.025,g.w.upper[sl]-.025),bounds=list(zip(g.w.lower[sl]+.025,g.w.upper[sl]-.025)),constraints=[{'type':'ineq','fun':constraint}],method='SLSQP',options={'maxiter':100,'ftol':1e-9});point,gaps,full=calc(tuple(fit.x));selfbad=H.inspect(full);row={'digit':a.digit,'link':a.link,'digit_q':fit.x.tolist(),'point_knife_m':point.tolist(),'normal_gap_m':float(point[0]-.0095),'minimum_constraint':float(constraint(fit.x).min()),'self':selfbad,'optimizer':str(fit.message)};rows.append(row);print(json.dumps(row),flush=True)
  if abs(row['normal_gap_m'])<.0002 and constraint(fit.x).min()>-.01 and not selfbad:best=row;break
 result={'scope':__doc__,'source':a.source,'rows':rows,'accepted_geometry':best};(a.output/'geometry.json').write_text(json.dumps(result,indent=2));record('temporary_opposite_side_bearing_geometry_complete',[str(a.output/'geometry.json')],{'accepted_geometry':best,'rows':rows},next_step='If feasible, native acquiringactualopposite-side bearing then thumbfree capability beforecap+B; otherwise different grip geometry, no per-finger live tracker')
if __name__=='__main__':main()
