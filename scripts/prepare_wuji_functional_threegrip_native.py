"""Geometry-only initial hypothesis: independent bilateral index/middle support plus thumb slider. Not A proof."""
import numpy as np,json
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
p=Path('runs/flat-table-20261006/development/functional-threegrip-native-20261006');p.mkdir();s=json.load(open('runs/flat-table-20261006/preparation/functional-threegrip-inverse-20261006/candidate.json'));q=np.array(s['hand_q']);aq=np.array(s['arm_q']);O=np.array(s['object_world']);L=np.array(s['wrist_in_knife']);h=WujiKinematics();names=s['active_links'];mat=np.array(s['material_points']);targets=np.array(s['targets']);ids=[np.arange(4),np.arange(4,8),np.arange(16,20)]
def solve(ts,seed):
 qq=seed.copy()
 for n,m,t,ii in zip(names,mat,ts,ids):
  def r(x):
   q1=qq.copy();q1[ii]=x;T=L@h.forward(q1)[n];return np.r_[(T[:3,:3]@m+T[:3,3]-t)*200,(x-qq[ii])*.001]
  f=least_squares(r,np.clip(qq[ii],h.lower[ii]+.001,h.upper[ii]-.001),bounds=(h.lower[ii]+.001,h.upper[ii]-.001),max_nfev=80);qq[ii]=f.x
 return qq
closed=targets.copy();closed[0,0]-=.0015;closed[1,0]+=.0015;closed[2,1]-=.0008;rows=[];prior=q.copy()
for t in np.arange(0,4.9,1/30):
 u=np.clip(t/.4,0,1);ts=targets*(1-u)+closed*u;ts[2,2]+=.03*np.clip((t-1.5)/1.7,0,1);prior=solve(ts,prior);rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=prior.tolist()))
np.savez_compressed(p/'takeover.npz',object_state=np.r_[O[:3,3],Rotation.from_matrix(O[:3,:3]).as_quat(),np.zeros(6)],robot_q=np.r_[aq,q],estimated_robot_velocity=np.zeros(27),slider_q=np.array(0.),slider_velocity=np.array(0.),issued_target=np.r_[aq,q],issued_target_history=np.array([np.r_[aq,q]]))
(p/'support.json').write_text(json.dumps(dict(rows=rows,scope=__doc__)));c=json.load(open('runs/flat-table-20261006/development/overhang-progressive-close-20261006/command.json'));c[c.index('--output')+1]=str(p/'simulation');c[c.index('--recorded-handoff')+1]=str(p);c[c.index('--recorded-support-command')+1]=str(p/'support.json');(p/'command.json').write_text(json.dumps(c,indent=2));print(p)
