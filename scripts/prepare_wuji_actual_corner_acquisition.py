"""From actual newly transported tableclamp, release and acquire new functional index/thumb grip. No later resets."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
p=Path('runs/flat-table-20261006/development/actual-corner-functional-acquire-20261006');p.mkdir();s=json.load(open('runs/flat-table-20261006/preparation/actual-corner-index-thumb-20261006/candidate.json'));start=np.load('runs/flat-table-20261006/recorded-final-place-12s/takeover.npz');k=G2Kinematics();h=WujiKinematics();q=np.array(s['hand_q']);aq=np.array(s['arm_q']);W=k.forward(aq);L=np.array(s['wrist_in_knife']);names=s['active_links'];materials=np.array(s['material_points']);targets=np.array(s['targets']);ids=np.r_[np.arange(4),np.arange(16,20)]
def fingers(ts,seed):
 def r(x):
  qq=seed.copy();qq[ids]=x;F=h.forward(qq);out=[]
  for n,m,t in zip(names,materials,ts):
   T=L@F[n];out.extend((T[:3,:3]@m+T[:3,3]-t)*220)
  out.extend((x-seed[ids])*.001);return out
 fit=least_squares(r,np.clip(seed[ids],h.lower[ids]+.001,h.upper[ids]-.001),bounds=(h.lower[ids]+.001,h.upper[ids]-.001),max_nfev=100);qq=seed.copy();qq[ids]=fit.x;return qq
opened=targets.copy();opened[1,1]+=.020;openq=fingers(opened,q);pressed=targets.copy();pressed[0,1]+=.0015;pressed[1,1]-=.001;closeq=fingers(pressed,q);oldW=k.forward(start['robot_q'][:7]);oldhigh=oldW.copy();oldhigh[2,3]+=.15;outside=W.copy();outside[0,3]-=.10;above=outside.copy();above[2,3]+=.15;lift=W.copy();lift[2,3]+=.16;rows=[];seed=start['robot_q'][:7];errors=[]
for t in np.arange(0,3,1/30):
 u=t/3;T=oldW.copy();T[2,3]+=.15*u;seed,e=k.solve_near(T,seed);hq=start['issued_target'][7:]*(1-u)+openq*u;rows.append(dict(time_s=float(t),arm_q=seed.tolist(),hand_q=hq.tolist()))
end,e=k.solve(above,aq)
for t in np.arange(3,8,1/30):
 u=(t-3)/5;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=(seed*(1-u)+end*u).tolist(),hand_q=openq.tolist()))
seed=end
keys=[(8,above),(11,outside),(14,W),(17,W),(21,lift),(23,lift)]
for (ta,A),(tb,B) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);T=A.copy();T[:3,3]=(1-u)*A[:3,3]+u*B[:3,3];seed,e=k.solve_near(T,seed);errors.append(e);hq=openq if ta<14 else openq*(1-u)+closeq*u if ta==14 else closeq;rows.append(dict(time_s=float(t),arm_q=seed.tolist(),hand_q=hq.tolist()))
(p/'support.json').write_text(json.dumps(dict(rows=rows,scope=__doc__,max_ik_error_m=max(e['position_m'] for e in errors))));c=json.load(open('runs/flat-table-20261006/development/final-clamp-small-correction-20261006/command.json'));c[c.index('--output')+1]=str(p/'simulation');c[c.index('--recorded-support-command')+1]=str(p/'support.json');c[c.index('--seconds')+1]='23';(p/'command.json').write_text(json.dumps(c));print('maxik',max(e['position_m'] for e in errors))
