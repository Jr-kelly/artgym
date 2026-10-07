"""Prepare a short native direct-pickup test from feasible side geometry."""
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=10);p.add_argument('--compression-m',type=float,default=.0015);p.add_argument('--grip-feedback',action='store_true');p.add_argument('--video',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=json.load(a.candidate.open());L=np.array(s['wrist_in_knife']);q=np.array(s['hand_q']);O=np.array(s['object_world']);O[:2,3]=[.45,-.4];O[:3,:3]=Rotation.from_euler('x',-90,degrees=True).as_matrix();g=DigitGeometry(knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));O=g.knife_geometry.table_pose(O);k=G2Kinematics();W=O@L;high=W.copy();high[2,3]+=.10;arm,e=k.solve(high,np.array(s['arm_q']));assert e['position_m']<.001,e
N=np.array([[1,0,0] if 'thumb' in n else [-1,0,0] for n in s['active_links']]);V={n:np.concatenate([v for v,_ in g.meshes[n]]) for n in s['active_links']}
def point(h,n,d):
 T=L@g.w.forward(h)[n]
 if s.get('functional_front'):return T[:3,:3]@np.asarray(s['material_points'][n])+T[:3,3]
 v=V[n]@T[:3,:3].T+T[:3,3];pr=v@d;weight=np.exp((pr-pr.max())/.0004);return weight@v/weight.sum()
opened=q.copy();closed=q.copy();diagnostics=[]
for name,d in zip(s['active_links'],N):
 finger=name.split('_')[2];ids=[g.w.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];target=point(q,name,d)
 for out,delta in [(opened,-.012),(closed,a.compression_m)]:
  wanted=target+d*delta
  def res(x):
   h=q.copy();h[ids]=x;return np.r_[(point(h,name,d)-wanted)*300,(x-q[ids])*.01]
  fit=least_squares(res,q[ids],bounds=(g.w.lower[ids]+.01,g.w.upper[ids]-.01),max_nfev=80,diff_step=1e-5);out[ids]=fit.x;diagnostics.append({'finger':finger,'delta_m':delta,'error_m':float(np.linalg.norm(point(out,name,d)-wanted))})
spec=dict(duration_s=a.seconds,initial_arm_q=arm.tolist(),wrist_in_knife=L.tolist(),open_q=opened.tolist(),close_q=closed.tolist(),lift_m=.12,pose_bias_x_m=0.)
if a.grip_feedback:
 spec.update(material_points=s['material_points'],grip_normal_reference_N={'hand_r_index_pad_link':.7,'hand_r_middle_pad_link':.7,'hand_r_thumb_pad_link':1.4},hand_kp=json.load(open('runs/flat-table-20261006/direct/development/material-lift-v5/simulation/physics.json'))['kp'][7:])
prefix=dict(duration_s=a.seconds,physical_initial_xy=O[:2,3].tolist(),physical_initial_yaw_deg=0.,physical_initial_object_world=O.tolist(),pose_source='Explicit initialenvelope; oneactual poseobservation1s',direct_pickup=spec,rows=[dict(time_s=float(t),arm_q=arm.tolist(),hand_q=opened.tolist()) for t in np.arange(0,a.seconds+1/30,1/30)])
(a.output/'prefix.json').write_text(json.dumps(prefix));(a.output/'preparation.json').write_text(json.dumps(dict(candidate=str(a.candidate),compression_m=a.compression_m,ik=e,digits=diagnostics),indent=2))
c=json.load(open('runs/flat-table-20261006/validation/quality-final-nominal-v1/command.json'));c[0]=sys.executable
for flag in ['--postpush-pose-update','--relax-idle-ring','--scheduled-target-holds']:
 if flag in c:c.remove(flag)
for flag in ['--postlift-regrasp','--prefix-pose-adaptation','--residual-checkpoint','--proprioceptive-pressure-config']:
 if flag in c:
  i=c.index(flag);del c[i:i+2]
if not a.video:c.remove('--video')
c[c.index('--seconds')+1]='.04';c[c.index('--flat-table-prefix')+1]=str(a.output/'prefix.json');c[c.index('--output')+1]=str(a.output/'simulation');c+=['--grasp-only'];(a.output/'command.json').write_text(json.dumps(c,indent=2))
record('direct_native_close_lift_start',[str(a.output/'command.json'),str(a.output/'preparation.json')],config={'uncertainty':'Sidecontact geometrynormalapproximations can lift55g withouttablepenetration?','decision':'Wholeheld+actualopposingcontacts allows supporttransfer/roll; failedcontact identifiespad/table/load issue','compression_m':a.compression_m,'seconds':a.seconds},updates={'active_jobs':[str(a.output)]},next_step='Inspectactualcontact firstdivergence; no samegeometry seedretry')
subprocess.run(c,check=True);record('direct_native_close_lift_finished',[str(a.output/'simulation/trace.npz')],updates={'active_jobs':[]},next_step='Evaluateactualwholeclear/opposition/table thennextdirectmechanism')
