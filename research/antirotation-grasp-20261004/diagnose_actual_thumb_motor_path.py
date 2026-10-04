"""Offline motor geometry versus contact path; actual trace is evaluation only."""
import json,numpy as np
from pathlib import Path
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_antirotation_goal import record
b=Path('runs/antirotation-grasp-20261004');p=b/'continuous-plans-v1/opposed-table-strong';plan=json.loads((p/'settled-operation-grasp.json').read_text());r=json.loads((p/'interpolation-repaired-reference-v5.json').read_text());g=DigitGeometry();q0=np.array(plan['close_q']);w=np.array(plan['wrist_in_knife']);normal=np.array(plan['contact_normals'][0]);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']])
def site(q):
 m=w@g.w.forward(q)['hand_r_thumb_pad_link'];a=v@m[:3,:3].T+m[:3,3];pr=a@normal;weights=np.exp(-(pr-pr.min())/.0002);return weights@a/weights.sum()
rows=[]
for row in r['rows']:
 touch=q0.copy();touch[16:]=row['q_thumb'];motor=q0.copy();motor[16:]=row['q_thumb_preloaded'];rows.append(dict(shift_m=row['shift_m'],touch_site_knife_m=site(touch).tolist(),motor_site_knife_m=site(motor).tolist(),nominal_motor_minus_touch_site_m=(site(motor)-site(touch)).tolist()))
touch_travel=np.array(rows[-1]['touch_site_knife_m'])-np.array(rows[0]['touch_site_knife_m']);motor_travel=np.array(rows[-1]['motor_site_knife_m'])-np.array(rows[0]['motor_site_knife_m']);out=dict(scope='Offline knownmodel motor-point geometry only; targets are virtualimpedance positions, not measuredforce or realcontact. Actualcontact checked separately.',rows=rows,touch_path_delta_m=touch_travel.tolist(),motor_path_delta_m=motor_travel.tolist(),initial_motor_site_m=site(q0).tolist());dest=p/'motor-contact-trajectory-diagnosis-v1.json';dest.write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'}));record('nominal_thumb_motor_vs_contact_trajectory_diagnosed',evidence=str(dest),config={'touch_path_delta_m':touch_travel.tolist(),'motor_path_delta_m':motor_travel.tolist()},next='If preloadcollisionprojection shortens tangential motortravel, replace with directlyconstrained geometricmotorpath before further pressure/unchangedtraining')
