"""Prepare table-side truepad grasp with a reserved reachable G2 approach."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
c=json.loads(a.candidate.read_text());k=G2Kinematics();g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));O=np.array(c['object_world']);L=np.array(c['wrist_in_knife']);W=O@L;heights=np.linspace(0,.12,5);seeds=[];seed=np.array(c['arm_q'])
for height in heights:
 G=W.copy();G[2,3]+=height;seed,_=k.solve(G,seed);seeds.append(seed)
seeds=np.array(seeds);x0=np.r_[seeds.ravel(),[0,0]];lo=np.r_[np.tile(k.lower+.12,5),[-.07,-.07]];hi=np.r_[np.tile(k.upper-.12,5),[.07,.07]]
def residual(x):
 qs=x[:-2].reshape(5,7);r=[]
 for q,z in zip(qs,heights):
  G=W.copy();G[:2,3]+=x[-2:];G[2,3]+=z;A=k.forward(q);r.extend((A[:3,3]-G[:3,3])*50);r.extend(Rotation.from_matrix(G[:3,:3].T@A[:3,:3]).as_rotvec()*20)
 r.extend(x[-2:]*.02);r.extend(((qs-seeds)*.0001).ravel());r.extend((np.diff(qs,axis=0)*.001).ravel());return np.array(r)
record('direct_truepad_approach_preparation_started',[str(a.output),str(a.candidate)],config={'uncertainty':'All5 approachheight knots G2 .12radreserve and exacttruepadgrip atonewithin-table placement, openhandwholemesh clear?','decision':'ReservedFK<.2mm/.5mrad/openendpointself0 permitsfresh10s, otherwise no native launch'})
fit=least_squares(residual,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=120);errors=residual(fit.x)[:30].reshape(5,6);poserr=np.linalg.norm(errors[:,:3],axis=1)/50;roterr=np.linalg.norm(errors[:,3:],axis=1)/20;O[:2,3]+=fit.x[-2:];W=O@L;q=np.array(c['hand_q']);opened=q.copy();diags=[]
for n in c['active_links']:
 f=n.split('_')[2];ids=[g.w.names.index('hand_r_'+f+'_joint'+str(j)) for j in range(1,5)];m=np.array(c['material_points'][n]);target=np.array(c['contact_points'][c['active_links'].index(n)]);target[0]+=(-.003 if f=='thumb' else .003);x0=q[ids].copy()
 def open_res(x):
  h=opened.copy();h[ids]=x;F=g.w.forward(h);T=L@F[n];r=list((T[:3,:3]@m+T[:3,3]-target)*300)
  for name,parts in g.meshes.items():
   if '_'+f+'_' not in name:continue
   A=W@F[name]
   for v,_ in parts:r.append(min(0,float((v@A[:3,:3].T+A[:3,3])[:,2].min()-.7515))*500)
  r.extend(min(0,z['gap_lower_bound_m']-.0001)*180 for z in g.gaps(h,L,0,f));r.extend((x-x0)*.02);return np.array(r)
 solution=least_squares(open_res,np.clip(x0,g.w.lower[ids]+.04,g.w.upper[ids]-.04),bounds=(g.w.lower[ids]+.04,g.w.upper[ids]-.04),max_nfev=80,diff_step=1e-5);opened[ids]=solution.x;diags.append(dict(link=n,point_error_m=float(np.linalg.norm(open_res(solution.x)[:3])/300)))
qarm=fit.x[:-2].reshape(5,7);closedself=HandIntersection().inspect(q);openself=HandIntersection().inspect(opened);diag=dict(shift_table_xy_m=fit.x[-2:].tolist(),arm_position_errors_m=poserr.tolist(),arm_rotation_errors_rad=roterr.tolist(),minimum_arm_command_margin_rad=float(np.minimum(qarm-k.lower,k.upper-qarm).min()),open_diagnostics=diags,closed_self=closedself,open_self=openself)
(a.output/'diagnostics.json').write_text(json.dumps(diag,indent=2));print(json.dumps(diag),flush=True)
assert poserr.max()<.0002 and roterr.max()<.0005 and not closedself and not openself
base=json.loads(Path('runs/flat-table-20261006/direct/preparation/fresh-thumb-only-clearance-v103/pickup-prefix.json').read_text());s=base['direct_pickup'];s.update(initial_arm_q=qarm[-1].tolist(),wrist_in_knife=L.tolist(),open_q=opened.tolist(),close_q=q.tolist(),material_points=c['material_points'],arm_command_margin_rad=.12);s.pop('thumb_only_table_clearance_m',None);s.pop('free_thumb_command_margin_rad',None);base['physical_initial_object_world']=O.tolist();base['physical_initial_xy']=O[:2,3].tolist();base['rows'][0].update(arm_q=qarm[-1].tolist(),hand_q=opened.tolist());base['route_revision']='Reserved truefrontpad sideopposition; exactsameasset/physics. G2all5heightknots .12radcommandreserve and3mmopenjaw/table1.5mm. Candidate contactlongitudinaltargets explicit.'
(a.output/'pickup-prefix.json').write_text(json.dumps(base,indent=2));record('direct_truepad_approach_preparation_finished',[str(a.output/'pickup-prefix.json'),str(a.output/'diagnostics.json')],config=diag,next_step='One fresh10s actual contact/wholepickup/reserve test; no numericalpose acceptance')
