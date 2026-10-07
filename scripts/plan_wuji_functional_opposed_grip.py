"""Jointly fit a functional longitudinal grip and its temporary thumb pinch.

One design, inferred from existing operating/table geometry. Table initial
and two cap endpoints share the bearing layout. No pose becomes a physical
state; only a new native tabletop episode can establish task progress.
"""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
 B=Path('runs/flat-table-20261006/direct');source=B/'preparation/direct-functional-initial-reach-v670/candidate.json';opfile=B/'preparation/direct-operating-ring-corner-v665/candidate.json';out=B/'preparation/direct-functional-joint-opposed-grip-v706';out.mkdir(exist_ok=False);c=json.loads(source.read_text());op=json.loads(opfile.read_text());L0=np.asarray(c['wrist_in_knife']);q0=np.asarray(c['hand_q']);O=np.asarray(c['table_object_world']);g=DigitGeometry(knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));check=HandIntersection();ids=np.r_[0:8,12:16];names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4'];thumb='hand_r_thumb_pad_link';V={n:np.concatenate([v for v,_ in g.meshes[n]]) for n in names+[thumb]};mat=np.asarray(op['poses'][0]['thumb_material']);theta=c['ring_corner_angle_rad'];directions=[np.array([1.,0,0]),np.array([0,1.,0]),np.array([-np.cos(theta),np.sin(theta),0.])];baseline_slider=float(np.load(Path(op['source'])/'takeover.npz')['slider_q']);parts=[g.knife_geometry.collision_parts(baseline_slider+j*.022) for j in range(2)]
 x0=np.r_[np.zeros(6),q0[ids],q0[16:],op['poses'][0]['hand_q'][16:],op['poses'][1]['hand_q'][16:]]
 lo=np.r_[[-.03,-.015,-.035],[-.5]*3,g.w.lower[ids]+.035,np.tile(g.w.lower[16:]+.035,3)];hi=np.r_[[.03,.045,.035],[.5]*3,g.w.upper[ids]-.035,np.tile(g.w.upper[16:]-.035,3)];x0=np.clip(x0,lo+1e-6,hi-1e-6);clock=time.time();calls=[0]
 cfg=dict(candidate='D706',grasp_end='Pendingnewfreshnative; geometry670/665 arepriors only',support_layout='LongitudinalIndex-X/Middleback/Ring+Xrear, proximalThumbpad+Xinitial; jointlyallowwrist andRingposture toleaveThumbroom',control='Onejointinitial/cap22mmgeometricdesign. Original55g/PD/effort/friction/resistance/limits/collisionpreserved',evidence='704primarytrackstilllosesloadedgrip;705fixedThumbblocked16.3mm andRing3/4intersection2.2/2.5mm',uncertainty='Can jointwrist/bearinglayout retain naturaltableaccess while temporaryThumbopposition and22mmcapgeometry coexist?',decision='Clearwholeinitial/path -> implementfreshpickup andownactualcontinuation; blocked -> bindinggrasp/table/capconstraint changesnextgeometry, no fixedThumbseedpool')
 e=record('functional_joint_opposed_grip_start',[str(source),str(opfile),str(out),'scripts/plan_wuji_functional_opposed_grip.py'],config=cfg,updates={'active_planning_jobs':[str(out)]},next_step=cfg['decision'])
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(cfg)+'\n')
 def decode(x):
  L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3];qs=[]
  for j in range(3):
   q=q0.copy();q[ids]=x[6:18];q[16:]=x[18+j*4:22+j*4];qs.append(q)
  return L,qs
 def surface(L,F,n,d):
  T=L@F[n];v=V[n]@T[:3,:3].T+T[:3,3];s=v@d;w=np.exp((s-s.max())/.00015);m=w@V[n]/w.sum();return T[:3,:3]@m+T[:3,3],m
 def residual(x):
  L,qs=decode(x);r=[]
  for j,q in enumerate(qs):
   F=g.w.forward(q)
   for n,d in zip(names,directions):
    P,_=surface(L,F,n,d)
    if n==names[0]:r.extend([(P[0]+.0095)*650,max(0.,abs(P[1])-.0038)*600,(P[2]-.0066)*80])
    elif n==names[1]:r.extend([(P[1]+.004)*650,max(0.,abs(P[0])-.0088)*600,(P[2]+.004)*100])
    else:r.extend([(P[0]-.0095)*500,(P[1]+.004)*500,(P[2]+.055)*40,max(0.,abs(P[2]+.0525)-.0175)*700])
   T=L@F[thumb]
   if j==0:
    P,_=surface(L,F,thumb,np.array([-1.,0,0]));r.extend([(P[0]-.0095)*700,(P[1]+.001)*450,(P[2]+.008)*60,max(0.,abs(P[2]+.0075)-.0175)*700]);r.extend((T[:3,0]-np.array([-1.,0,0]))*.08)
    W=O@L
    for n,p in g.meshes.items():
     M=W@F[n]
     r.extend(min(0.,float((v@M[:3,:3].T+M[:3,3])[:,2].min()-.7502))*1300 for v,_ in p)
   else:
    P=T[:3,:3]@mat+T[:3,3];r.extend((P-np.array([-.003,.006,-.033+.022*(j-1)]))*700)
   # Positive certificates save distant projections; potential interference
   # keeps all original hull faces. Native collision filters never change.
   r.extend(min(0.,a['gap_lower_bound_m']-.0002)*750 for a in g.pair_gaps(q,check.pairs,certify_clearance_m=.0002))
   for digit in ['index','middle','ring','thumb']:
    for a in g.gaps(q,L,baseline_slider+.022*max(0,j-1),digit,frames=F,knife_parts=parts[max(0,j-1)]):
     bearing=a['knife_link']=='link_0' and (a['hand_link'] in names or (j==0 and a['hand_link'] in [thumb,'hand_r_thumb_link4']))
     cap=j>0 and a['knife_link']=='link_1' and a['hand_link']==thumb
     r.append(min(0.,a['gap_lower_bound_m']+(.00035 if bearing or cap else -.0002))*750)
  r.append(max(0.,.6-L[1,0])*4);r.extend((x-x0)*.015);calls[0]+=1
  if calls[0]%250==0:
   recordrow=dict(calls=calls[0],cost=float(np.dot(r,r)),elapsed_s=time.time()-clock);print(json.dumps(recordrow),flush=True);(out/'checkpoint.json').write_text(json.dumps(dict(progress=recordrow,x=x.tolist()),indent=2))
  return np.asarray(r)
 fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=100,diff_step=1e-5);L,qs=decode(fit.x);poses=[]
 for j,q in enumerate(qs):
  F=g.w.forward(q);contacts=[]
  for n,d in zip(names,directions):
   P,m=surface(L,F,n,d);contacts.append(dict(link=n,point=P.tolist(),material=m.tolist(),inward_knife=d.tolist()))
  T=L@F[thumb];P,initial_m=surface(L,F,thumb,np.array([-1.,0,0])) if j==0 else (T[:3,:3]@mat+T[:3,3],mat)
  poses.append(dict(hand_q=q.tolist(),contacts=contacts,thumb_point=P.tolist(),thumb_material=initial_m.tolist(),thumb_error_m=float(np.linalg.norm(P-np.array([.0095,-.001,-.008] if j==0 else [-.003,.006,-.033+.022*(j-1)]))),self=check.inspect(q)))
 W=O@L;F=g.w.forward(qs[0]);floor=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,p in g.meshes.items() for v,_ in p);arm,ik=G2Kinematics().solve_near(W,np.asarray(c['arm_q']),max_step=1.5,minimum_margin=.06);eligible=not any(p['self'] for p in poses) and floor>.0001 and max(p['thumb_error_m'] for p in poses)<.0007 and ik['position_m']<.0005
 result=dict(candidate='D706',initial_source=str(source),operating_source=str(opfile),wrist_in_knife=L.tolist(),table_object_world=O.tolist(),table_yaw_degrees=c['table_yaw_degrees'],poses=poses,arm_q=arm.tolist(),arm_ik=ik,table_clearance_m=floor,palm_down_knife_Y=float(L[1,0]),geometry_permits_native=eligible,elapsed_s=time.time()-clock,scope=__doc__);(out/'candidate.json').write_text(json.dumps(result,indent=2));summary=dict(geometry_permits_native=eligible,thumb_errors_m=[p['thumb_error_m'] for p in poses],self=[p['self'] for p in poses],table_clearance_m=floor,arm_ik=ik,palm_down_knife_Y=float(L[1,0]),elapsed_s=result['elapsed_s']);print(json.dumps(summary),flush=True)
 e=record('functional_joint_opposed_grip_terminal',[str(out/'candidate.json')],config=summary,updates={'active_planning_jobs':[]},next_step='Eligible -> freshfunctionalopposedpickup; blocked -> onlybindinginitial/cap/tableconstraint, nohomogeneousnative')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')

if __name__=='__main__':main()
