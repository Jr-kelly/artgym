"""Development-only functional-grasp test. Artificial supported-edge hypothesis; not acquired A."""
import numpy as np,json
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
p=Path('runs/flat-table-20261006/development/overhang-functional-native-20261006');p.mkdir(exist_ok=False);s=json.load(open('runs/flat-table-20261006/preparation/overhang-slider-pinch-20261006/candidate.json'));k=G2Kinematics();h=WujiKinematics();q=np.array(s['hand_q']);aq=np.array(s['arm_q']);O=np.array(s['object_world']);L=np.array(s['wrist_in_knife']);names=s['active_links'];mat=np.array(s['material_points']);targets=np.array(s['targets']);ids=np.r_[np.arange(4),np.arange(16,20)]
def solve(ts,prior):
 def res(x):
  qq=prior.copy();qq[ids]=x;F=h.forward(qq);r=[]
  for n,m,t in zip(names,mat,ts):
   T=L@F[n];r.extend((T[:3,:3]@m+T[:3,3]-t)*250)
  r.extend((x-prior[ids])*.002);return r
 f=least_squares(res,prior[ids],bounds=(h.lower[ids]+.001,h.upper[ids]-.001),max_nfev=70);qq=prior.copy();qq[ids]=f.x;return qq
pressed=targets.copy();pressed[0,1]+=.002;pressed[1,1]-=.002;closed=solve(pressed,q);frames=[];prior=closed;seed=aq.copy();W=k.forward(aq)
for t in np.arange(0,4.9,1/30):
 lift=np.clip((t-.6)/.8,0,1);T=W.copy();T[2,3]+=.14*lift;seed,e=k.solve_near(T,seed)
 move=np.clip((t-1.6)/1.6,0,1);ts=pressed.copy();ts[1,2]+=.030*move;prior=solve(ts,prior);frames.append(dict(time_s=float(t),arm_q=seed.tolist(),hand_q=prior.tolist()))
# This artificial geometry is only a fresh development episode, never a reset inside complete A→B.
np.savez_compressed(p/'takeover.npz',object_state=np.r_[O[:3,3],__import__('scipy').spatial.transform.Rotation.from_matrix(O[:3,:3]).as_quat(),np.zeros(6)],robot_q=np.r_[aq,q],estimated_robot_velocity=np.zeros(27),slider_q=np.array(0.),slider_velocity=np.array(0.),issued_target=np.r_[aq,closed],issued_target_history=np.array([np.r_[aq,closed]]))
(p/'support.json').write_text(json.dumps(dict(rows=frames,scope=__doc__),indent=2));c=json.load(open('runs/flat-table-20261006/development/recorded-hold-20261006/command.json'));c[c.index('--output')+1]=str(p/'simulation');c[c.index('--recorded-handoff')+1]=str(p);c[c.index('--seconds')+1]='4.9';c+=['--recorded-support-command',str(p/'support.json')];(p/'command.json').write_text(json.dumps(c,indent=2));print(p)
