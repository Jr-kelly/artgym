"""Finite physical transport to retained B pickup pose; no slider training."""
from scripts.wuji_table_transfer_learning_env import TableTransferLearning
import numpy as np,json,torch,shutil
from pathlib import Path
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.record_wuji_flat_table_event import record
p=Path('runs/flat-table-20261006/learning/b-compatible-transport-20261006');p.mkdir();data=p/'data';data.mkdir();src=Path('runs/flat-table-20261006/learning/table-transfer-20261006')
for n in ['scene.json','takeover.npz','prefix.npz']:shutil.copy2(src/n,data/n)
s=np.load(data/'takeover.npz');O=transform(s['object_state'][:3],s['object_state'][3:7]);k=G2Kinematics();W=k.forward(s['robot_q'][:7]);L=np.linalg.inv(O)@W;goal=transform([.31,-.6295,.7541],Rotation.from_euler('zx',[45,90],degrees=True).as_quat())
# Use exact retained B planar orientation rather than Euler convention ambiguity.
goal=np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/localization.json'))['object_world_matrix']);rot=Rotation.from_matrix(goal[:3,:3]@O[:3,:3].T).as_rotvec();seed=s['robot_q'][:7].copy();path=[];errors=[]
for t in np.arange(0,12,1/30):
 u=np.clip((t-1)/8,0,1);u=u*u*(3-2*u);obj=O.copy();obj[:3,:3]=Rotation.from_rotvec(rot*u).as_matrix()@O[:3,:3];obj[:3,3]=O[:3,3]*(1-u)+goal[:3,3]*u;seed,e=k.solve_near(obj@L,seed);cmd=s['issued_target'].copy();cmd[:7]=seed+s['issued_target'][:7]-s['robot_q'][:7];path.append(cmd);errors.append(e['position_m'])
np.savez_compressed(data/'learn-path.npz',targets=path);record('b_compatible_table_transport_batch_started',[str(data/'learn-path.npz')],dict(uncertainty='Physical clamp transport can preserve planarBorientation andcorner while handload coordinated?',decision='Safe planarend->native thenoldBpickup; otherwise revise approach notslider.',episodes=32,goal=goal.tolist(),max_ik_error_m=max(errors)),updates=dict(active_jobs=['b-compatible-transport-search']),next_step='Read physicalBpose terminal, no proxy-onlysuccess.')
e=TableTransferLearning(n=32,seed=61067,data=str(data));rng=np.random.default_rng(61067);ids=np.r_[np.arange(7,15),np.arange(23,27)];prior=np.array(json.load(open('runs/flat-table-20261006/learning/table-contact-search-20261006/best.json'))['parameters']);params=prior+rng.normal(0,.12,(32,12));params[0]=prior;trace=[]
try:
 for i in range(len(path)):
  u=np.clip(i/90,0,1);u=u*u*(3-2*u);motor=e.path[i].expand(e.n,-1).clone();motor[:,ids]+=e.tensor(params)*float(u);e.servo(motor);trace.append(dict(object=e.rb[:,e.object_index].cpu().numpy().copy(),target=e.command_target.cpu().numpy().copy(),q=e.dof[:,:,0].cpu().numpy().copy()))
 obj=e.rb[:,e.object_index].cpu().numpy();pos=np.linalg.norm(obj[:,:3]-goal[:3,3],axis=1);ang=(Rotation.from_quat(obj[:,3:7]).inv()*Rotation.from_matrix(goal[:3,:3])).magnitude();valid=(obj[:,2]>.75)&(obj[:,2]<.775);score=np.where(valid,pos+.035*ang,10.);ix=int(score.argmin());result=dict(index=ix,position_error_m=float(pos[ix]),angle_error_rad=float(ang[ix]),parameters=params[ix].tolist(),object_final=obj[ix].tolist(),scope='Recorded36s episode development, Bcompatibility candidate, no fullflowproof');(p/'result.json').write_text(json.dumps(result,indent=2));np.savez_compressed(p/'best-rollout.npz',**{k:np.array([r[k][ix] for r in trace]) for k in trace[0]});print(json.dumps(result),flush=True);record('b_compatible_table_transport_batch_finished',[str(p/'result.json')],result,updates=dict(active_jobs=[]),next_step='Native materialtransport candidate thenoldBactualacquisition; no repeatedbatch.')
finally:e.close()
