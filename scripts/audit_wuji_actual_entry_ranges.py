"""Read-only audit of actual learned trajectories, not new target/reset trials."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_measured_hold_reference import _thumb_geometry,_thumb_frame
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def audit(source,f,z=None,env_index=None,query_stride=3,pose_motion=False):
 z=np.load(source/'actual-regrasp-trace.npz') if z is None else z;g,chain=_thumb_geometry();vertices=f.vertices;rows=[];counts=dict(frames=len(z['dof']),closed_slider=0,settled_bearing=0,cap_near=0,reserve=0,range_candidates=0,exact_reference_eligible=0);stage_slider=float(z['dof'][0,27,0]);beg=time.monotonic();fallen=False
 motions=np.asarray(z['object'])[:,7:13].copy()
 if pose_motion:
  poses=np.asarray(z['object'])[:,:7];motions[0]=0;motions[1:,:3]=np.diff(poses[:,:3],axis=0)*30;motions[1:,3:]=(Rotation.from_quat(poses[1:,3:])*Rotation.from_quat(poses[:-1,3:]).inv()).as_rotvec()*30
 counts.update(Hsafe_candidates=0,H_exact_queries=0,full31_queries=0)
 for i in range(len(z['dof'])):
  q=z['dof'][i,:27,0].astype(float);slider=float(z['dof'][i,27,0]);o=z['object'][i];O=transform(o[:3],o[3:7]);clear=o[2]-.75-abs(O[2,2])*.072-abs(O[2,1])*.006-abs(O[2,0])*.0095
  fallen=fallen or clear<.01;closed=abs(slider-stage_slider)<.002;settled=not fallen and clear>.025 and np.linalg.norm(motions[i,:3])<.12 and np.linalg.norm(motions[i,3:])<.8;reserve=float(np.minimum(q[23:]-g.w.lower[16:],g.w.upper[16:]-q[23:]).min())>.075
  counts['closed_slider']+=int(closed);counts['settled_bearing']+=int(settled);counts['reserve']+=int(reserve)
  P=f.kin.forward(q[:7])@_thumb_frame(q[7:],chain);world=vertices@P[:3,:3].T+P[:3,3];local=(world-O[:3,3])@O[:3,:3];center=f.g.knife_geometry.joint_xyz+f.g.knife_geometry.axis*slider;distance=float(np.linalg.norm(np.maximum(abs(local-center)-np.array([.007,.002,.032])/2,0),axis=1).min());near=distance<.004;counts['cap_near']+=int(near)
  if closed and settled and reserve and near:
   counts['range_candidates']+=1
   if i%query_stride:continue
   if pose_motion:
    counts['H_exact_queries']+=1;bad=f.H.inspect(q[7:])
    if bad:continue
    counts['Hsafe_candidates']+=1
   counts['full31_queries']+=1
   a=f.assess(q,O,slider);counts['exact_reference_eligible']+=int(a['reference_eligible']);rows.append(dict(frame=i,age_s=(i+1)/30,cap_distance_m=distance,slider_q_m=slider,linear_speed_m_s=float(np.linalg.norm(motions[i,:3])),affordance=a))
 return dict(source=str(source),env_index=env_index,exact_query_stride=query_stride,motion_sensor='actual-pose-difference-30hz' if pose_motion else 'raw-reported-rigidbody',counts=counts,elapsed_s=time.monotonic()-beg,rows=rows,scope='Actual trajectory only; 4mm cap window and .12m/s broadened diagnostic range, exactfull30mm+actualH required; no B capacityclaim. Existing live gate remains unchanged.')

def main():
 p=argparse.ArgumentParser();p.add_argument('--pose-motion',action='store_true');p.add_argument('--source',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 record('actual_entry_range_audit_started',[str(s) for s in a.source],dict(question='Do closedslider/settledbearing actual states pass fullB workspace but get excluded by the narrow cap gate?',decision='Ifyes, physicallytest sameepisodeB from that range; ifno, continue actualworkspace learning without changing gate'),next_step='Read actual range results; no staticgeometry target counts as physicalcapacity')
 try:
  f=FunctionalEntryAffordance();results=[]
  for source in a.source:
   many=source/'actual-regrasp-traces.npz'
   if many.exists():
    data=np.load(many);dof=data['dof'];objects=data['object'];valid=data['prefix_valid'];assert dof.ndim==4 and objects.shape[:2]==dof.shape[:2]
    for env in np.flatnonzero(valid):results.append(audit(source,f,dict(dof=dof[:,env],object=objects[:,env]),int(env),query_stride=1,pose_motion=a.pose_motion))
   else:results.append(audit(source,f,query_stride=1 if a.pose_motion else 3,pose_motion=a.pose_motion))
  (a.output/'audit.json').write_text(json.dumps(results,indent=2));print(json.dumps([{k:v for k,v in r.items() if k!='rows'} for r in results]),flush=True)
 finally:record('actual_entry_range_audit_terminal',[str(a.output/'audit.json')],next_step='Use measured closedslider/settled fullstroke states to select necessary native B test, otherwise preserve gate andlearn')

if __name__=='__main__':main()
