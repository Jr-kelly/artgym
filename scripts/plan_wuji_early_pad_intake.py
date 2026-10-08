"""Static functional entry diagnostic: whole pad surface + original clearances.
No physical arrival, carry or pushing claim. No scene/controller setters here.
"""
import json,argparse,datetime
from pathlib import Path
import numpy as np
from functools import lru_cache
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_measured_hold_reference import measured_hold_path
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initial-axial',type=float,default=-.026);p.add_argument('--source',type=Path,default=Path('runs/flat-table-20261006/direct/recorded/current-C560-no-extra-load-flip-v565-6p1'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 source=a.source;z=np.load(source/'takeover.npz');g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');h=g.w;kin=G2Kinematics();q=z['robot_q'][7:].astype(np.float64);W=kin.forward(z['robot_q'][:7]);O=transform(z['object_state'][:3],z['object_state'][3:7]);L=np.linalg.inv(O)@W;s=float(z['slider_q']);vertices=np.concatenate([v for v,n in g.meshes['hand_r_thumb_pad_link']]);target=np.array([0.,.00612,a.initial_axial+s]);parts=g.knife_geometry.collision_parts(s)
 @lru_cache(maxsize=4096)
 def sample(values):
  full=q.copy();full[16:]=values;F=h.forward(full);T=L@F['hand_r_thumb_pad_link'];v=vertices@T[:3,:3].T+T[:3,3];w=np.exp(-(v[:,1]-v[:,1].min())/.0002);point=w@v/w.sum()
  gaps=g.gaps(full,L,s,'thumb',frames=F,knife_parts=parts,certify_clearance_m=.0001)+g.self_gaps(full,'thumb',frames=F,certify_clearance_m=.0001)+g.pair_gaps(full,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')],certify_clearance_m=.0001)
  return point,v[:,1].min(),np.array([r['gap_lower_bound_m'] for r in gaps])
 def objective(x):
  point,y,gap=sample(tuple(x));return float(np.sum(((point-target)*200)**2)+.001*np.sum((x-q[16:])**2))
 def constraint(x):
  point,y,gap=sample(tuple(x));return np.r_[(gap+.00005)*1000,(y-.00602)*1000,(.0031-abs(point[0]))*1000,(.008-abs(point[2]-target[2]))*1000]
 seeds=[np.array([1.0181323,.08630635,.85918193,.27026213]),np.array([.936627,.0148336,.618154,.767749]),np.array([1.5,.1,.5,-.2]),np.array([1.,.3,1.,.3]),q[16:]]
 rows=[];accepted=None
 for seed in seeds:
  fit=minimize(objective,np.clip(seed,h.lower[16:]+.025,h.upper[16:]-.025),method='SLSQP',bounds=list(zip(h.lower[16:]+.025,h.upper[16:]-.025)),constraints=[dict(type='ineq',fun=constraint)],options={'maxiter':120,'ftol':1e-10});full=q.copy();full[16:]=fit.x;point,y,gaps=sample(tuple(fit.x));bad=HandIntersection().inspect(full);path=None;error=None
  if constraint(fit.x).min()>-.01 and not bad:
   try:path,audit=measured_hold_path(full,L[:3,:3].T@np.array([0,1,0.]),L[:3,:3].T@np.array([0,0,1.]),np.linspace(0,.025,26));error=max(r['FK_position_error_m'] for r in audit['rows'])
   except ValueError as e:error=str(e)
  row=dict(thumb_q=fit.x.tolist(),pad_surface_knife_m=point.tolist(),actual_vertex_min_y_m=float(y),minimum_constraint=float(constraint(fit.x).min()),self=bad,optimizer_message=str(fit.message),full_path_error=error);rows.append(row);print(json.dumps(row),flush=True)
  if path is not None and constraint(fit.x).min()>-.01 and not bad:accepted={'hand_q':full.tolist(),'path_thumb_q':path.tolist(),'audit':audit};break
 result=dict(source=str(source),wrist_in_knife=L.tolist(),rows=rows,accepted=accepted,scope=__doc__);(a.output/'geometry.json').write_text(json.dumps(result,indent=2))
 record('early_whole_pad_functional_intake_geometry_complete',[str(a.output/'geometry.json')],{'accepted':accepted is not None,'rows':rows},next_step='If wholepad/25mm feasible, native ideal diagnostic bearing+adaptedB; no actualregrasp/tablegoal claim')
if __name__=='__main__':main()
