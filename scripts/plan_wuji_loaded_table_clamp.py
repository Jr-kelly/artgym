"""Jointly fit three real carrier sites, table clearance and Thumb reserve.

Uses actual development contact materials; this is geometry, not native lift
evidence. No physical asset, PD, effort, collision or object state is changed.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser()
 for n in ['trial','prefix','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 z=np.load(a.trial/'trace.npz');clock=z['time'];elapsed=clock-clock[0]+1/30;i=int(abs(elapsed-5).argmin())
 native=[json.loads(l) for l in open(a.trial/'wrap-contact-physical-steps.jsonl')]
 spec=json.loads(a.prefix.read_text());g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics()
 q0=z['q'][i].astype(float);Osource=transform(z['object'][i,:3],z['object'][i,3:7]);L0=np.linalg.inv(Osource)@k.forward(z['arm_q'][i]);F0=g.w.forward(q0)
 # Start from the actual naturally resting object, before clamp forces tilt it.
 O=transform(z['object'][0,:3],z['object'][0,3:7]);materials={};targets={};normal_local={};normal_target={}
 for finger in ['index','middle','thumb']:
  window=[v for r in native if abs(r['time_s']-clock[i])<.1 for v in r['contacts'] if '_'+finger+'_' in v['hand_link'] and v['knife_link']=='link_0']
  if not window:raise ValueError('Missing actual carrier contact '+finger)
  names=sorted(set(v['hand_link'] for v in window))
  n=max(names,key=lambda n:sum(v['normal_magnitude_N'] for v in window if v['hand_link']==n))
  C=[v for v in window if v['hand_link']==n]
  materials[n]=np.mean([v['position_hand_link_m'] for v in C],axis=0)
  T=L0@F0[n];P=T[:3,:3]@materials[n]+T[:3,3];targets[n]=P.copy();targets[n][1]=min(P[1],-.0018)
  N=np.mean([v['force_normal_contribution_knife_N'] for v in C],axis=0);N/=np.linalg.norm(N);normal_local[n]=T[:3,:3].T@N;normal_target[n]=N
 ids=np.r_[0:8,16:20];x0=np.r_[L0[:3,3],Rotation.from_matrix(L0[:3,:3]).as_rotvec(),q0[ids]]
 lo=np.r_[x0[:3]-.012,x0[3:6]-.18,g.w.lower[ids]+.05];hi=np.r_[x0[:3]+.012,x0[3:6]+.18,g.w.upper[ids]-.05]
 initial_gaps={f:g.gaps(q0,L0,float(z['slider'][i]),f) for f in ['index','middle','thumb']}
 def decode(x):
  L=transform(quaternion=Rotation.from_rotvec(x[3:6]).as_quat());L[:3,3]=x[:3];q=q0.copy();q[ids]=x[6:];F=g.w.forward(q);return L,q,F
 def residual(x):
  L,q,F=decode(x);W=O@L;r=[]
  for n,m in materials.items():
   T=L@F[n];r.extend((T[:3,:3]@m+T[:3,3]-targets[n])*350)
   r.extend((T[:3,:3]@normal_local[n]-normal_target[n])*.5)
  for n,parts in g.meshes.items():
   T=W@F[n]
   for v,_ in parts:r.append(min(0,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7508))*1800)
  for f in ['index','middle','thumb']:
   for j,v in enumerate(g.gaps(q,L,float(z['slider'][i]),f)):
    threshold=.0001
    if v['knife_link']=='link_0' and v['hand_link'] in materials:threshold=min(-.0001,initial_gaps[f][j]['gap_lower_bound_m'])
    r.append(min(0,v['gap_lower_bound_m']-threshold)*1000)
   r.extend(min(0,v['gap_lower_bound_m']-.0001)*250 for v in g.self_gaps(q,f,certify_clearance_m=.0001))
  r.extend((x-x0)*.035);return np.array(r)
 e=record('coupled_loaded_table_clamp_geometry_start',[str(a.output)],config=dict(uncertainty='Can allthree realpad contacts jointly clear table with >=50mradThumb reserve after singlecarrier/raisedwrist failures?',source=str(a.trial),desired_top_side_knife_y_m=-.0018,table_clearance_m=.0008),next_step='Feasible allcarrier/tablegeometry -> compileoriginal wrench/preload nativepickup; infeasible -> altercontact topology or wrist range withspecificblock')
 Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
 start=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);L,q,F=decode(fit.x);W=O@L
 arm,ik=k.solve_near(W,z['arm_q'][i].astype(float),max_step=.5,minimum_margin=.06)
 errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@m+(L@F[n])[:3,3]-targets[n])) for n,m in materials.items()}
 clearance=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts)
 out=dict(wrist_in_knife=L.tolist(),hand_q=q.tolist(),arm_q=arm.tolist(),arm_ik=ik,
  material_points={n:v.tolist() for n,v in materials.items()},contact_targets={n:v.tolist() for n,v in targets.items()},support_errors_m=errors,
  normal_directions={n:v.tolist() for n,v in normal_target.items()},table_clearance_m=clearance,
  minimum_hand_margin_rad=float(np.minimum(q-g.w.lower,g.w.upper-q).min()),self_intersections=HandIntersection().inspect(q),elapsed_s=time.time()-start,
  source_actual_elapsed_s=float(elapsed[i]),original_physics=True,scope=__doc__)
 out['permits_native_preparation']=bool(max(errors.values())<.0005 and clearance>.0005 and not out['self_intersections'] and ik['position_m']<.0001)
 (a.output/'candidate.json').write_text(json.dumps(out,indent=2));summary={k:v for k,v in out.items() if k not in ['wrist_in_knife','hand_q','arm_q','material_points','contact_targets','normal_directions']};print(json.dumps(summary))
 e=record('coupled_loaded_table_clamp_geometry_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Passing geometry -> native original boundedwrench loading/lift; failed -> exactgeometricblock')
 Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(summary)+'\n')
 if not out['permits_native_preparation']:raise SystemExit(2)

if __name__=='__main__':main()
