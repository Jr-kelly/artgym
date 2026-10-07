"""Functional operating grip first, with real bearing surface rolling.

Original actual643 is a geometry prior, never a reset or successful new grip.
Index stays on its actual -X side, Middle is established anterior to the
proximal thumb, Ring4 remains a rear back bearing. The initial table grasp
will be inferred only after this functional geometry is demonstrated.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ring-side',action='store_true');p.add_argument('--ring-corner',action='store_true');p.add_argument('--seed',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 s=np.load(a.source/'takeover.npz');trial,rows,end=source_contacts(a.source);g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics()
 O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);q0=s['robot_q'][7:].astype(float);ids=np.r_[0:8,12:16]
 names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4'];thumb='hand_r_thumb_pad_link';V={n:np.concatenate([v for v,_ in g.meshes[n]]) for n in names}
 cs=[c for r in rows for c in r['contacts'] if c['hand_link']==thumb and c['knife_link']=='link_1'];m=np.mean([c['position_hand_link_m'] for c in cs],axis=0);T=L0@g.w.forward(q0)[thumb];N=np.sum([c['force_normal_contribution_knife_N'] for c in cs],axis=0);N/=np.linalg.norm(N);localN=T[:3,:3].T@N
 x0=np.r_[np.zeros(6),q0[ids],q0[16:],q0[16:],.0025,.0088,.004,-.046]
 lo=np.r_[[-.05]*3,[-.65]*3,g.w.lower[ids]+.04,np.tile(g.w.lower[16:]+.04,2),-.0088,-.0088,-.012,-.064]
 hi=np.r_[[.05]*3,[.65]*3,g.w.upper[ids]-.04,np.tile(g.w.upper[16:]-.04,2),.0088,.0088,.022,-.028]
 if a.seed:
  seed=json.loads(a.seed.read_text());SL=np.asarray(seed['wrist_in_knife']);x0[:3]=SL[:3,3]-L0[:3,3];x0[3:6]=Rotation.from_matrix(SL[:3,:3]@L0[:3,:3].T).as_rotvec();x0[6:18]=np.asarray(seed['poses'][0]['hand_q'])[ids];x0[18:22]=seed['poses'][0]['hand_q'][16:];x0[22:26]=seed['poses'][1]['hand_q'][16:];x0[26]=seed['poses'][0]['contacts'][1]['target'][0];x0[28]=seed['poses'][0]['contacts'][0]['target'][2];x0[29]=seed['poses'][0]['contacts'][2]['target'][2]
 if a.ring_side:
  lo[27]=-.0039;hi[27]=.0039;x0[27]=-.003
 if a.ring_corner:
  x0=np.r_[x0,.785398];lo=np.r_[lo,.05];hi=np.r_[hi,1.52]
 x0=np.clip(x0,lo+1e-7,hi-1e-7);calls=[0];start=time.time()
 def decode(x):
  L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3];qs=[]
  for j in range(2):
   q=q0.copy();q[ids]=x[6:18];q[16:]=x[18+j*4:22+j*4];qs.append(q)
  return L,qs
 def surface(L,F,n,axis,side,corner_angle=None):
  T=L@F[n];P=V[n]@T[:3,:3].T+T[:3,3];d=P@np.array([-np.cos(corner_angle),np.sin(corner_angle),0.]) if n==names[2] and corner_angle is not None else side*P[:,axis];w=np.exp((d-d.max())/.00012);mat=w@V[n]/w.sum();return T[:3,:3]@mat+T[:3,3],mat
 def targets(x):return [[-.0095,.0009,x[28]],[x[26],-.004,-.004],[.0095,-.004,x[29]] if a.ring_corner else [.0095,x[27],x[29]] if a.ring_side else [x[27],-.004,x[29]]]
 def residual(x):
  L,qs=decode(x);r=[]
  for j,q in enumerate(qs):
   F=g.w.forward(q);shift=.022*j
   for n,ax,side,tgt in zip(names,[0,1,0 if a.ring_side else 1],[1,1,-1 if a.ring_side else 1],targets(x)):
    P,_=surface(L,F,n,ax,side,x[30] if a.ring_corner else None);r.extend((P-np.asarray(tgt))*450)
   T=L@F[thumb];tgt=np.array([-.003,.006,-.033+shift]);r.extend((T[:3,:3]@m+T[:3,3]-tgt)*500);r.extend((T[:3,:3]@localN-N)*.15)
   for finger in ['index','middle','ring','thumb']:
    for v in g.gaps(q,L,float(s['slider_q'])+shift,finger,frames=F):
     allowed=(v['hand_link'] in names and v['knife_link']=='link_0') or (v['hand_link']==thumb and v['knife_link']=='link_1')
     r.append(min(0.,v['gap_lower_bound_m']-(-.00025 if allowed else .0003))*1000)
    r.extend(min(0.,v['gap_lower_bound_m']-.0002)*500 for v in g.self_gaps(q,finger,certify_clearance_m=.0002,frames=F))
   r.extend(min(0.,v['gap_lower_bound_m']-.0003)*1000 for v in g.pair_gaps(q,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link',thumb)]))
  r.extend((x-x0)*.015);calls[0]+=1
  if calls[0]%400==0:print(json.dumps(dict(calls=calls[0],cost=float(np.dot(r,r)),elapsed_s=time.time()-start)),flush=True)
  return np.asarray(r)
 e=record('operating_surface_grip_start',[str(a.output)],config=dict(candidate='D665' if a.ring_corner else 'D664' if a.ring_side else 'D663',source=str(a.source),grasp_end='New functional geometry inferredfrom actual643; initialnotyetdesigned',support_layout='Index-X,frontMiddleback,Ring4actual+X/-Ycorner; freelyrolling diagonalcontactnormal' if a.ring_corner else 'Index-X, frontMiddle realback, Ring4+X opposedside insteadof blockedpureback' if a.ring_side else 'Actual Index-X, frontMiddle realbacksurface, rearRing4backsurface; rolling material andgrip',control='Functional geometry first, no loadedinhand translation and no staticgain',uncertainty='663pureback maxY fallsoutsideX9.74;664pureside minX fallsoutsideY-4.74. Can realknuckle diagonalcorner surface carry, withoutforcedpurefacet?' if a.ring_corner else '663frontMiddle/Thumbclear but RingmaxYsurface fallsoutsideknifeX9.74mm. Does actualRing4innerXside provideopposedpinch withoutforcedbackcenter?' if a.ring_side else '662rigid15mmshift blocksThumb. Can jointoperatinggrip withactual Indexside androllingmaterial establishfrontMiddle whileproximal22mmThumb remainsclear?',decision='Eligible -> reverse tabletopsidegrasp fromthisfunctional geometry, then nativepickup. Blocked -> exactThumb/body/support reach determinesdifferenttopology'),next_step='Do not runnative on blocked662 or reuse659forwardtransition')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
 fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=100,diff_step=1e-5);L,qs=decode(fit.x);poses=[];check=HandIntersection()
 for j,q in enumerate(qs):
  F=g.w.forward(q);contacts=[]
  for n,axis,side,tgt in zip(names,[0,1,0 if a.ring_side else 1],[1,1,-1 if a.ring_side else 1],targets(fit.x)):
   P,mat=surface(L,F,n,axis,side,fit.x[30] if a.ring_corner else None);contacts.append(dict(link=n,material=mat.tolist(),point=P.tolist(),target=tgt,error_m=float(np.linalg.norm(P-tgt))))
  T=L@F[thumb];P=T[:3,:3]@m+T[:3,3];target=[-.003,.006,-.033+j*.022];gaps=g.gaps(q,L,float(s['slider_q'])+j*.022,'thumb')
  poses.append(dict(hand_q=q.tolist(),contacts=contacts,thumb_material=m.tolist(),thumb_normal_local=localN.tolist(),thumb_point=P.tolist(),thumb_target=target,thumb_error_m=float(np.linalg.norm(P-target)),self=check.inspect(q),min_thumb_body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0')))
 arm,ik=k.solve_near(O@L,s['robot_q'][:7].astype(float),max_step=1.5,minimum_margin=.06)
 eligible=not any(p['self'] for p in poses) and max(p['thumb_error_m'] for p in poses)<.0005 and max(c['error_m'] for p in poses for c in p['contacts'])<.0005 and min(p['min_thumb_body_gap_m'] for p in poses)>.0001 and ik['position_m']<.0005
 out=dict(candidate='D665' if a.ring_corner else 'D664' if a.ring_side else 'D663',source=str(a.source),geometry_permits_native=eligible,wrist_in_knife=L.tolist(),arm_q=arm.tolist(),arm_ik=ik,ring_corner_angle_rad=float(fit.x[30]) if a.ring_corner else None,poses=poses,elapsed_s=time.time()-start,scope=__doc__)
 (a.output/'candidate.json').write_text(json.dumps(out,indent=2));summary=dict(geometry_permits_native=eligible,thumb_errors_m=[p['thumb_error_m'] for p in poses],support_errors_m=[[c['error_m'] for c in p['contacts']] for p in poses],self_poses=sum(bool(p['self']) for p in poses),arm_ik=ik,elapsed_s=out['elapsed_s']);print(json.dumps(summary),flush=True)
 e=record('operating_surface_grip_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Eligible -> infer newtabletop initialgrip aroundD663; blocked -> exactreach/collisionevidence selects changedbearingtopology')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')

if __name__=='__main__':main()
