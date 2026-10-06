"""Actual flat-to-held motor history, then middle proximal support before releasing thumb."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.wuji_kinematics import WujiKinematics
s=json.load(open('runs/flat-table-20261006/preparation/acquired-middle-link4-v107/candidate.json'));old=json.load(open('runs/flat-table-20261006/preparation/clamped-extraction-v104/prefix.json'));rows=old['rows'].copy();h=WujiKinematics();L=np.array(s['wrist_in_knife']);q=np.array(s['measured_hand_q']);motor=np.array(rows[-1]['hand_q']);point=np.array(s['material_point']);n='hand_r_middle_link4';wanted=np.array(s['target']);wanted[1]+=.002
seed=np.array(s['middle_q'])
def res(x):
 qq=q.copy();qq[4:8]=x;T=L@h.forward(qq)[n];return np.r_[(T[:3,:3]@point+T[:3,3]-wanted)*200,(x-seed)*.004]
f=least_squares(res,np.clip(seed,h.lower[4:8]+.001,h.upper[4:8]-.001),bounds=(h.lower[4:8]+.001,h.upper[4:8]-.001),max_nfev=80);closed=motor.copy();closed[4:8]=f.x;arm=rows[-1]['arm_q']
for t in np.arange(47,50,1/30):
 u=(t-47)/3;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=arm,hand_q=(motor*(1-u)+closed*u).tolist()))
for t in np.arange(50,53,1/30):rows.append(dict(time_s=float(t),arm_q=arm,hand_q=closed.tolist()))
# Separate handoff test: free thumb by moving it away from cap, only after real middle contact can be inspected.
free=closed.copy();free[16]+= -.35;free[18]+=.25;free=np.clip(free,h.lower,h.upper)
for t in np.arange(53,56,1/30):
 u=(t-53)/3;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=arm,hand_q=(closed*(1-u)+free*u).tolist()))
for t in np.arange(56,59,1/30):rows.append(dict(time_s=float(t),arm_q=arm,hand_q=free.tolist()))
old.update(duration_s=59,rows=rows,scope=__doc__,stage_events=[dict(time_s=47,event='middle_support_entry'),dict(time_s=53,event='thumb_release_diagnostic'),dict(time_s=56,event='released_hold')]);p=Path('runs/flat-table-20261006/preparation/acquired-middle-handoff-v108');p.mkdir();(p/'prefix.json').write_text(json.dumps(old,indent=2));print('middle motor',f.x,'res',np.linalg.norm(res(f.x)[:3])/200)
