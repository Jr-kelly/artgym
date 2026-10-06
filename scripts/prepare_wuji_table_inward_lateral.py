"""Actual24s supportedknife -> new rear-side push; no later state assignments."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
p=Path('runs/flat-table-20261006/development/table-inward-lateral-native-20261006');p.mkdir();s=json.load(open('runs/flat-table-20261006/preparation/table-inward-transfer-20261006/candidate.json'));z=np.load('runs/flat-table-20261006/recorded-table-v123-24s/takeover.npz');k=G2Kinematics();h=WujiKinematics();aq=np.array(s['arm_q']);q=np.array(s['hand_q']);W=k.forward(aq);O=np.array(s['object_world']);F=h.forward(q)[s['material_link']];m=np.array(s['material_point']);point=F[:3,:3]@m+F[:3,3];normal=F[:3,0];worldpoint=W[:3,:3]@point+W[:3,3];N=W[:3,:3]@normal;outside=worldpoint+N*.065;above=outside.copy();above[2]+=.12;press=worldpoint-N*.003;drag=press-N*.095;release=drag+N*.025;release[2]+=.12;rows=[];seed=z['robot_q'][:7];init=z['issued_target'];
def solve(target,seed):
 T=W.copy();T[:3,3]+=target-worldpoint;out,e=k.solve_near(T,seed);return out
seed=solve(above,aq);keys=[(0,above),(2,above),(3,outside),(4,worldpoint),(4.5,press),(8,drag),(9,release),(10,release)]
for (ta,A),(tb,B) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);seed=solve(A*(1-u)+B*u,seed);arm=init[:7]*(1-t/2)+seed*(t/2) if t<2 else seed;hand=init[7:]*(1-t/2)+q*(t/2) if t<2 else q;rows.append(dict(time_s=float(t),arm_q=arm.tolist(),hand_q=hand.tolist()))
(p/'support.json').write_text(json.dumps(dict(rows=rows,scope=__doc__)));c=json.load(open('runs/flat-table-20261006/development/recorded-hold-20261006/command.json'));c[c.index('--output')+1]=str(p/'simulation');c[c.index('--recorded-handoff')+1]='runs/flat-table-20261006/recorded-table-v123-24s';c[c.index('--seconds')+1]='10';c+=['--recorded-support-command',str(p/'support.json')];(p/'command.json').write_text(json.dumps(c,indent=2));print(p)
