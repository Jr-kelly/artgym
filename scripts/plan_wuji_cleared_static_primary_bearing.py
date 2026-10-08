"""Axially free new bearing route while retaining the verified actual three-primary grasp.

Uses a recorded actual stable grasp; fixed wrist and old bearing fingers. Full original
new-finger collision patch clears corner before entering -Y back. No per-finger servo,
new pressure search or geometry modification. Physical load still needs native proof.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--digit',choices=['ring','pinky'],default='ring');p.add_argument('--endpoint-only',action='store_true');p.add_argument('--free-corner-x',action='store_true');p.add_argument('--free-idle-ring',action='store_true');p.add_argument('--resume-route',type=Path);p.add_argument('--resume-pose-count',type=int,default=8);p.add_argument('--endpoint-reference',type=Path);p.add_argument('--version',default='v919');p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g;h0=z['robot_q'][7:].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);name='hand_r_'+a.digit+'_pad_link';ids=np.arange(12,16)if a.digit=='ring'else np.arange(8,16)if a.free_idle_ring else np.arange(8,12)
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 V=np.concatenate([v for v,N in g.meshes[name]])
 def geometry(q):
  h=h0.copy();h[ids]=q;F=g.w.forward(h);T=L@F[name];P=V@T[:3,:3].T+T[:3,3];w=np.exp((P[:,1]-P[:,1].max())/.0002);return h,F,P,w@P/w.sum()
 _,_,P,first=geometry(h0[ids]);assert a.endpoint_only or P[:,0].min()>.0125;start=time.monotonic();record('static_primary_axial_free_bearing_geometry_started_'+a.version,[str(a.source)],dict(scope=__doc__,source_foot=first.tolist(),axial_range_m=[-.07,-.03]),next_step='Check fixed-primary wholepatch path before physicalrun; unreachable ->newcontactmode instead of squeeze/trackergains')
 initial_depth={}
 for c in g.gaps(h0,L,float(z['slider_q']),a.digit):initial_depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.000005)
 anchors=[first[:2],np.array([first[0],-.0094]),np.array([.006,-.0094]),np.array([.006,-.0044])];q=h0[ids].copy();rows=[];failure=None
 if a.resume_route:
  old=json.loads(a.resume_route.read_text());assert old['source']==str(a.source)and old['digit']==a.digit;rows=old['rows'][:a.resume_pose_count];q=np.array(rows[-1]['hand_q'])[ids];anchors[1]=np.array([rows[4]['foot_knife_m'][0],-.0094])
 for index in ([12]if a.endpoint_only else range(13)):
  if not a.endpoint_only and index<len(rows):continue
  stage=min(2,max(0,(index-1)//4));alpha=(index-4*stage)/4;wanted=anchors[stage]*(1-alpha)+anchors[stage+1]*alpha;phase=['clear-back-corner','enter-back-face','acquire-back-face'][stage];previous=q.copy()
  def residual(x):
   if time.monotonic()-start>90:raise TimeoutError('Bounded fixed-primary reachability check')
   h,F,P,foot=geometry(x);goal_xy=wanted.copy()
   if stage==0 and a.free_corner_x:goal_xy[0]=np.clip(foot[0],min(.025,first[0]),first[0])
   r=list((foot[:2]-goal_xy)*800);r.append((foot[2]-np.clip(foot[2],-.07 if stage==2 else -.09,-.03 if stage==2 else -.025))*1000)
   if stage==0:r.append(min(0.,P[:,0].min()-.0125)*1400)
   else:r.append(max(0.,P[:,1].max()+(.009 if stage==1 else .0042))*1400)
   r.extend(min(0.,c['gap_lower_bound_m']-initial_depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))])*1400 for c in g.gaps(h,L,float(z['slider_q']),a.digit,frames=F,certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002))
   if a.free_idle_ring:
    for fraction in [.25,.5,.75]:
     mh,mF,mP,mfoot=geometry(previous*(1-fraction)+x*fraction);r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(mh,f.H.pairs,certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']+.0002)*1400 for d in ['pinky','ring']for c in g.gaps(mh,L,float(z['slider_q']),d,frames=mF,certify_clearance_m=.0002))
    r.extend(min(0.,c['gap_lower_bound_m']+.0002)*1400 for c in g.gaps(h,L,float(z['slider_q']),'ring',frames=F,certify_clearance_m=.0002))
   r.extend((x-previous)*.02);return np.array(r)
  try:
   if index==12 and a.endpoint_reference:
    end=json.loads(a.endpoint_reference.read_text());assert end['passed']and end['source']==str(a.source)and end['digit']==a.digit;candidate=np.array(rows[-1]['hand_q']);newids=np.arange(8,12)if a.digit=='pinky'else np.arange(12,16);candidate[newids]=np.array(end['rows'][-1]['hand_q'])[newids];q=candidate[ids]
   else:q=previous if index==0 else least_squares(residual,previous,bounds=(g.w.lower[ids]+.025,g.w.upper[ids]-.025),max_nfev=80,diff_step=1e-5).x
  except TimeoutError as e:failure=str(e);break
  h,F,P,foot=geometry(q);actual_goal=wanted.copy()
  if stage==0 and a.free_corner_x:actual_goal[0]=np.clip(foot[0],min(.025,first[0]),first[0])
  error=float(np.linalg.norm(foot[:2]-actual_goal));bad=f.H.inspect(h);row=dict(index=index,phase=phase,hand_q=h.tolist(),arm_q=z['robot_q'][:7].tolist(),wrist_in_knife=L.tolist(),foot_knife_m=foot.tolist(),target_xy_m=wanted.tolist(),error_m=error,pad_bounds_knife_m=[P.min(0).tolist(),P.max(0).tolist()],self=bad);rows.append(row);print(json.dumps(row),flush=True)
  if index==4 and a.free_corner_x:anchors[1]=np.array([foot[0],-.0094])
  if error>.0007 or bad or not (-.0701 if stage==2 else -.0901)<=foot[2]<=(-.0299 if stage==2 else -.0249):failure='Original fixed-primary reachability/collision constraint';break
 passed=len(rows)==(1 if a.endpoint_only else 13) and failure is None;out=dict(passed=passed,source=str(a.source),digit=a.digit,endpoint_only=a.endpoint_only,moving_joint_indices=ids.tolist(),rows=rows,failure=failure,elapsed_s=time.monotonic()-start,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));record('static_primary_axial_free_bearing_geometry_terminal_'+a.version,[str(a.output/'result.json')],out,next_step='Reachable fixed-primary route ->nativeactualnewbearing; unreachable ->different support transfer, not wristfeedback variantgrid')
if __name__=='__main__':main()
