"""Minimal nonthumb support test from actual rolled native contacts."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
s=np.load(a.source/'takeover.npz');h=WujiKinematics();q=s['robot_q'][7:].astype(float);issued=s['issued_target'][7:];O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@G2Kinematics().forward(s['robot_q'][:7]);manifest=json.load(open(a.source/'manifest.json'));trial=Path(manifest['source']).parent;clock=manifest['takeover_elapsed_s'];rr=[json.loads(l) for l in (trial/'wrap-contact-physical-steps.jsonl').open()];C=[c for r in rr if abs(r['time_s']-clock)<.08 for c in r['contacts'] if c['hand_link']=='hand_r_thumb_link4'];m=np.mean([c['position_hand_link_m'] for c in C],axis=0);name='hand_r_thumb_link4'
def point(x):
 T=L@h.forward(x)[name];return T[:3,:3]@m+T[:3,3]
start=point(q);seed=q[16:].copy();rows=[];errors=[]
for t in np.arange(0,7+1/60,1/30):
 target=start+[-.012*smooth((t-.5)/3),0,0]
 def res(v):
  x=q.copy();x[16:]=v;return np.r_[(point(x)-target)*250,(v-seed)*.015]
 fit=least_squares(res,seed,bounds=(h.lower[16:]+.025,h.upper[16:]-.025),max_nfev=70);seed=fit.x;x=q.copy();x[16:]=seed;cmd=issued.copy();cmd[16:]=seed+(issued[16:]-q[16:]);rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=np.clip(cmd,h.lower,h.upper).tolist()));errors.append(float(np.linalg.norm(point(x)-target)))
out=dict(rows=rows,source=str(a.source),material_point=m.tolist(),thumb_start_knife=start.tolist(),max_ik_error_m=max(errors),scope='Heldissued index/middle; onlythumb12mm outward, no state writes')
(a.output/'release.json').write_text(json.dumps(out,indent=2));print(out['max_ik_error_m']);record('direct_minimal_thumb_release_planned',[str(a.output/'release.json')],config={'actual_nonthumb_normal_y_N':.624,'weight_N':.53955,'uncertainty':'Actual backcorner supports upwardweight; can they balance without thumb?', 'decision':'Held no-thumb contact allows slider approach; loss means establish underside opposition first'},next_step='Native7s release tests existing measured upward support, not pressureincrease')
