"""Diagnostic test of a legal joint/command pressure estimate; no actor truth."""
import pathlib,json,numpy as np,yaml
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
R=pathlib.Path(__file__).resolve().parents[2];h=WujiKinematics();plan=json.loads((R/'research/robust-knife-family-20261003/handover-from-v25-v1.json').read_text());normal=np.array(plan['object_in_wrist'])[:3,1];kp=np.array(yaml.safe_load((R/'isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').read_text())['dof_props']['stiffness']);mesh=R/'assets/hands/wuji_artbot/meshes/collision/hand_r_thumb_pad_link.obj';v=np.array([np.fromstring(x[2:],sep=' ') for x in mesh.read_text().splitlines() if x.startswith('v ')]);rows=[]
for name in ['solver-nominal-v9','solver-heavy-baseline-v9','solver-heavy-coordinated-v9','solver-heavy-paced-v9']:
 z=np.load(R/'runs/support-pressure-20261003/demo'/name/'trace.npz');pred=[];actual=[];times=[]
 for i in np.flatnonzero((z['time']>=14)&(z['time']<36))[::5]:
  q=z['observed_q'][i].astype(float);t=h.forward(q)['hand_r_thumb_pad_link'];proj=(v@t[:3,:3].T+t[:3,3])@normal;w=np.exp(-(proj-proj.min())/.0002);w/=w.sum();point=w@v
  def fk(q):
   t=h.forward(q)['hand_r_thumb_pad_link'];return t[:3,:3]@point+t[:3,3]
  J=np.empty((3,4))
  for j in range(4):
   delta=np.zeros(20);delta[16+j]=1e-5;J[:,j]=(fk(q+delta)-fk(q-delta))/2e-5
  tau=kp[16:]*(z['target'][i,23:]-q[16:]);force=np.linalg.solve(J@J.T+np.eye(3)*1e-7,J@tau);estimate=-force@normal;pred.append(float(estimate));actual.append(float(z['pair_slider_pressure_mean_N'][i,0]));times.append(float(z['time'][i]))
 rows.append(dict(name=name,time=times,legal_joint_estimate_N=pred,measured_pair_normal_N=actual,estimate_mean_N=float(np.mean(pred)),actual_mean_N=float(np.mean(actual)),mae_N=float(np.mean(abs(np.array(pred)-actual))),correlation=float(np.corrcoef(pred,actual)[0,1]),scope='Knowncommand minus measuredjoints, originalKp and FK mesh/once nominalnormal. No live object/contact inestimate. Notactualconstantforce/hardwarefeedback; ignoresvelocity/friction/multiplecontacts. Truthonlycomparison.'))
(R/'research/support-pressure-20261003/joint-deflection-pressure-analysis-v1.json').write_text(json.dumps(rows,indent=2));print(json.dumps([{k:v for k,v in x.items() if k not in ['time','legal_joint_estimate_N','measured_pair_normal_N']} for x in rows]))
