"""Consume real thumb-released, tilted tableknife; joint wrist/index gait to functional grip without withdrawing index first."""
import json,numpy as np
from pathlib import Path
from scripts.g2_kinematics import G2Kinematics
p=Path('runs/flat-table-20261006/development/tilted-functional-handoff-20261006');p.mkdir();s=np.load('runs/flat-table-20261006/recorded-thumbreleased-table-4s/takeover.npz');g=json.load(open('runs/flat-table-20261006/preparation/actual-tilted-index-thumb-20261006/candidate.json'));aq=np.array(g['arm_q']);hq=np.array(g['hand_q']);q0=s['issued_target'][7:];arm0=s['issued_target'][:7];k=G2Kinematics();W=k.forward(aq);lift=W.copy();lift[2,3]+=.16;rows=[];seed=aq
for t in np.arange(0,15,1/30):
 u=np.clip((t-1)/8,0,1);u=u**3*(10-15*u+6*u*u);a=(1-u)*arm0+u*aq;q=(1-u)*q0+u*hq
 if t>=9:
  v=np.clip((t-9)/4,0,1);v=v**3*(10-15*v+6*v*v);T=W.copy();T[2,3]+=.16*v;seed,e=k.solve_near(T,seed);a=seed
 rows.append(dict(time_s=float(t),arm_q=a.tolist(),hand_q=q.tolist()))
(p/'support.json').write_text(json.dumps(dict(rows=rows,scope=__doc__)));c=json.load(open('runs/flat-table-20261006/development/actual-corner-passive-release-20261006/command.json'));c[c.index('--output')+1]=str(p/'simulation');c[c.index('--recorded-handoff')+1]='runs/flat-table-20261006/recorded-thumbreleased-table-4s';c[c.index('--recorded-support-command')+1]=str(p/'support.json');c[c.index('--seconds')+1]='15';(p/'command.json').write_text(json.dumps(c));print(p)
