"""Infer a natural tabletop initial grip from one functional operating grip.

Retains its anterior Middle region and opposed Index/Ring side topology.
Only motor geometry is planned. Thumb is initially free and table clear;
no unnecessary thumb-heel contact or identical initial/operating wrist is
required. A native pickup is required before any operating endpoint promotion.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
 p=argparse.ArgumentParser();p.add_argument('--operating',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=Path);p.add_argument('--table-yaw',type=float,default=0.);p.add_argument('--free-index-y',action='store_true');a=p.parse_args();c=json.loads(a.operating.read_text());assert c['geometry_permits_native'];a.output.mkdir(parents=True,exist_ok=False)
 g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();base=json.loads(Path('runs/flat-table-20261006/direct/development/current-504-pickup-live-flip-candidate-v560/prefix.json').read_text());O=g.knife_geometry.table_pose(np.asarray(base['physical_initial_object_world']))
 O[:3,:3]=Rotation.from_euler('z',a.table_yaw,degrees=True).as_matrix()@O[:3,:3]
 q0=np.asarray(c['poses'][0]['hand_q']);L0=np.asarray(c['wrist_in_knife']);angle=np.arctan2(L0[0,0],L0[1,0]);R=Rotation.from_euler('z',angle).as_matrix();S=L0.copy();S[:3,:3]=R@L0[:3,:3];S[:3,3]=R@L0[:3,3];S[1,3]=-.065
 names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4'];V={n:np.concatenate([v for v,_ in g.meshes[n]]) for n in names};targets=[v['target'] for v in c['poses'][0]['contacts']]
 x0=np.r_[S[:3,3],Rotation.from_matrix(S[:3,:3]).as_rotvec(),q0,c.get('ring_corner_angle_rad') or .785398];x0[22:26]=[1.2,.15,.4,.05]
 lo=np.r_[[-.17,-.13,-.19],x0[3:6]-1.2,g.w.lower+.045,.05];hi=np.r_[[.17,-.018,-.03],x0[3:6]+1.2,g.w.upper-.045,1.52];
 if a.seed:
  seed=json.loads(a.seed.read_text());SL=np.asarray(seed['wrist_in_knife']);x0[:3]=SL[:3,3];x0[3:6]=Rotation.from_matrix(SL[:3,:3]).as_rotvec();x0[6:26]=seed['hand_q']
 if a.free_index_y:
  x0=np.r_[x0,0.];lo=np.r_[lo,-.0039];hi=np.r_[hi,.0039]
 x0=np.clip(x0,lo+1e-7,hi-1e-7);start=time.time();calls=[0]
 def decode(x):return transform(x[:3],Rotation.from_rotvec(x[3:6]).as_quat()),x[6:26]
 def surface(L,F,n,axis,side,corner_angle=None):
  T=L@F[n];P=V[n]@T[:3,:3].T+T[:3,3];v=P@np.array([-np.cos(corner_angle),np.sin(corner_angle),0.]) if n==names[2] and corner_angle is not None else side*P[:,axis];w=np.exp((v-v.max())/.00012);m=w@V[n]/w.sum();return T[:3,:3]@m+T[:3,3],m
 def residual(x):
  L,q=decode(x);F=g.w.forward(q);r=[]
  for n,axis,side,tgt in zip(names,[0,1,0],[1,1,-1],targets):
   P,_=surface(L,F,n,axis,side,x[26]);target=np.asarray(tgt).copy()
   if n==names[0] and a.free_index_y:target[1]=x[27]
   r.extend((P-target)*500)
  W=O@L
  for link,parts in g.meshes.items():
   T=W@F[link]
   for v,_ in parts:r.append(min(0.,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7508))*1500)
  for finger in ['index','middle','ring','thumb','pinky']:
   for gap in g.gaps(q,L,0.,finger,frames=F):
    allowed=gap['hand_link'] in names and gap['knife_link']=='link_0';r.append(min(0.,gap['gap_lower_bound_m']-(-.00025 if allowed else .001 if finger=='thumb' else .0003))*1000)
   r.extend(min(0.,v['gap_lower_bound_m']-.0003)*600 for v in g.self_gaps(q,finger,certify_clearance_m=.0003,frames=F))
  r.extend(min(0.,v['gap_lower_bound_m']-.0003)*1000 for v in g.pair_gaps(q,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link','hand_r_thumb_pad_link')]))
  r.append(max(0.,.5-L[1,0])*3);r.extend((x-x0)*.01);calls[0]+=1
  if calls[0]%400==0:print(json.dumps(dict(calls=calls[0],cost=float(np.dot(r,r)),elapsed_s=time.time()-start)),flush=True)
  return np.asarray(r)
 e=record('table_grip_from_operating_start',[str(a.output),str(a.operating)],config=dict(candidate='D669' if a.free_index_y else 'D666',operating_grip=str(a.operating),table_yaw_degrees=a.table_yaw,free_index_y=a.free_index_y,seed=str(a.seed),support_layout='Preserveoperating anteriorMiddle/back andIndex-X/Ring4+Xopposedside regions; thumbfree initial',grasp_end='Pendingnewnative output; operatorgeometry notactual',control='Geometricinversion fromonefunctionalgrip; no oldpostgrasp idealstate',uncertainty='666 globalarmIK blocked105mm; naturalflat yaw180 puts newfunctionalgripinG2workspace. IndexfixedY0.9mm unnecessary; sideYnowfree. Can exacttable/cornergrip be acquired?' if a.free_index_y else 'Can functionalopposedside/back topology acquire55g on naturalflat table withdownwardpalm andfreeThumb, avoiding loadedMiddle14mmtranslation?',decision='Geometry/table/selfclear -> nativeinitialpickup; blocked -> exactlimiting contact/table andminimalrelaxation ofnot-goal constraint'),next_step='One initialsolve fromfunctionalD664, no seedpool or nativeblockedgeometry')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
 fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=110,diff_step=1e-5);L,q=decode(fit.x);F=g.w.forward(q);contacts=[];W=O@L
 for n,axis,side,tgt in zip(names,[0,1,0],[1,1,-1],targets):
  P,m=surface(L,F,n,axis,side,fit.x[26]);target=np.asarray(tgt).copy()
  if n==names[0] and a.free_index_y:target[1]=fit.x[27]
  contacts.append(dict(link=n,target=target.tolist(),point=P.tolist(),material=m.tolist(),error_m=float(np.linalg.norm(P-target))))
 clear=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts);bad=HandIntersection().inspect(q);arm,ik=k.solve_near(W,np.asarray(base['direct_pickup']['initial_arm_q']),max_step=2.,minimum_margin=.06)
 
 if a.table_yaw:
  global_arm,global_ik=k.solve(W,seed=arm,attempts=12);arm,ik=k.solve_near(W,global_arm,max_step=.3,minimum_margin=.06)
 eligible=clear>.0002 and not bad and max(v['error_m'] for v in contacts)<.0005 and L[1,0]>.4 and ik['position_m']<.0005
 out=dict(candidate='D669' if a.free_index_y else 'D666',operating=str(a.operating),geometry_permits_native=eligible,wrist_in_knife=L.tolist(),table_object_world=O.tolist(),hand_q=q.tolist(),arm_q=arm.tolist(),arm_ik=ik,contacts=contacts,ring_corner_angle_rad=float(fit.x[26]),table_yaw_degrees=a.table_yaw,table_hand_clearance_m=clear,self=bad,palm_down_knife_Y=float(L[1,0]),elapsed_s=time.time()-start,scope=__doc__);(a.output/'candidate.json').write_text(json.dumps(out,indent=2));summary={key:out[key] for key in ['geometry_permits_native','table_hand_clearance_m','palm_down_knife_Y','arm_ik','elapsed_s']};summary['contact_errors_m']=[v['error_m'] for v in contacts];summary['self']=bad;print(json.dumps(summary),flush=True)
 e=record('table_grip_from_operating_terminal',[str(a.output/'candidate.json')],config=summary,updates={'active_jobs':[]},next_step='Eligible -> native newinitialgrip andownactualflip; blocked -> exact table/reachfailure, no oldrecordedstage consumption')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')

if __name__=='__main__':main()
