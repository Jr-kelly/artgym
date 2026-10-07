"""Add a temporary thumb opponent to the functional longitudinal table grip.

D670 geometry is a motor design prior, not an actual acquired state. No
physics runs here. The earlier nonthumb pickup could not bear weight; this
checks a different opposing contact layout with useful proximal thumb reach.
"""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
 source=Path('runs/flat-table-20261006/direct/preparation/direct-functional-initial-reach-v670/candidate.json')
 out=Path('runs/flat-table-20261006/direct/preparation/direct-functional-initial-thumb-opponent-v705');out.mkdir(exist_ok=False)
 c=json.loads(source.read_text());g=DigitGeometry(knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));check=HandIntersection();q=np.asarray(c['hand_q']);L=np.asarray(c['wrist_in_knife']);O=np.asarray(c['table_object_world']);W=O@L;name='hand_r_thumb_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);target=np.array([.0095,-.001,-.026]);pairs=[p for p in check.pairs if any('_thumb_' in n for n in p)]
 config=dict(candidate='D705',grasp_end='Pendingfreshnative; D670longitudinalgeometry only',support_layout='Index-X,Middleback,Ring4+Xrear; addproximalThumbpad+X temporaryopposition insteadof D677transverseThumbheel-X',control='Onefixedwrist thumbIK feasibility; originaltable/limits/collisions, no forceincrease',uncertainty='Can functionalinitiallongitudinalgrip providea thumbsideopponent nearcap withoutconsumingoriginaljointreserve?',decision='Reachable/clear -> integratefourregioninitialpickup; blocked -> jointwrist/initialgripgeometry, no samephysicsretry')
 e=record('functional_initial_thumb_opponent_start',[str(source),str(out)],config=config,next_step=config['decision'])
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(config)+'\n')
 def decode(x):
  h=q.copy();h[16:]=x;F=g.w.forward(h);T=L@F[name];vv=V@T[:3,:3].T+T[:3,3];depth=-vv[:,0];w=np.exp((depth-depth.max())/.00015);mat=w@V/w.sum();return h,F,T[:3,:3]@mat+T[:3,3],mat
 parts=g.knife_geometry.collision_parts(0.)
 def residual(x):
  h,F,P,mat=decode(x);d=P-target;r=list(d*np.array([700.,500.,150.]));r.append(max(0.,abs(d[2])-.014)*500)
  normal=(L@F[name])[:3,0];r.extend((normal-np.array([-1.,0.,0.]))*.12)
  for a in g.gaps(h,L,0.,'thumb',frames=F,knife_parts=parts):
   bearing=a['knife_link']=='link_0' and a['hand_link'] in [name,'hand_r_thumb_link4'];r.append(min(0.,a['gap_lower_bound_m']+(.00025 if bearing else -.0002))*700)
  r.extend(min(0.,a['gap_lower_bound_m']-.0002)*700 for a in g.pair_gaps(h,pairs,certify_clearance_m=.0002))
  for n,p in g.meshes.items():
   if '_thumb_' not in n:continue
   T=W@F[n]
   r.extend(min(0.,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7502))*1200 for v,_ in p)
  r.extend((x-q[16:])*.008);return np.asarray(r)
 start=time.time();fit=least_squares(residual,q[16:],bounds=(g.w.lower[16:]+.04,g.w.upper[16:]-.04),max_nfev=80,diff_step=1e-5);h,F,P,mat=decode(fit.x);floor=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,p in g.meshes.items() for v,_ in p);bad=check.inspect(h);err=float(np.linalg.norm(P-target));result=dict(candidate='D705',source=str(source),wrist_in_knife=L.tolist(),table_object_world=O.tolist(),hand_q=h.tolist(),thumb_surface_point_knife_m=P.tolist(),thumb_material_point=mat.tolist(),target_knife_m=target.tolist(),endpoint_error_m=err,table_clearance_m=floor,self=bad,joint_margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min()),geometry_permits_native=err<.0007 and floor>.0001 and not bad,elapsed_s=time.time()-start,scope=__doc__);(out/'candidate.json').write_text(json.dumps(result,indent=2));summary={k:result[k] for k in ['geometry_permits_native','endpoint_error_m','thumb_surface_point_knife_m','table_clearance_m','self','joint_margin_rad','elapsed_s']};print(json.dumps(summary),flush=True)
 e=record('functional_initial_thumb_opponent_terminal',[str(out/'candidate.json')],config=summary,next_step='Clear -> implementfourcontactfunctionalinitialgrip; blocked -> samefunctionalwrist/grip jointgeometry solve')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')

if __name__=='__main__':main()
