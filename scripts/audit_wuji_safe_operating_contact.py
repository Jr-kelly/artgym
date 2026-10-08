"""Read-only archived H-safe contact progression, excluding failed frozen states."""
import argparse, json, hashlib, datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--rounds',type=int,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False);(a.output/'audit-source.py').write_text(Path(__file__).read_text())
 record('safe_operating_contact_audit_started',[str(a.source)],dict(rounds=a.rounds,question='Does contact-foot improve on actually held Hsafe trajectories, with reserve and closed slider? If yes continue to originalB; otherwise change grasp/contact mechanism rather than cost grids.'),next_step='Read actualvalid operatingfoot progression; do not use frozen/drop-state minima')
 f=FunctionalEntryAffordance();results=[]
 for round_no in a.rounds:
  src=a.source/('actual_all_envs_round_%03d'%round_no);z=np.load(src/'actual-regrasp-traces.npz');alive=z['prefix_valid'].copy();rows=[];counts=0
  for frame in range(14,len(z['dof']),15):
   for env in np.flatnonzero(alive):
    q=z['dof'][frame,env,:27,0].astype(float);o=z['object'][frame,env];O=transform(o[:3],o[3:7]);slider=float(z['dof'][frame,env,27,0]);clear=float(o[2]-.75-abs(O[2,2])*.072-abs(O[2,1])*.006-abs(O[2,0])*.0095)
    af=f.assess(q,O,slider,full_path=False)
    if clear<.01 or af['self_intersections']:alive[env]=False;continue
    if clear<=.025:continue
    counts+=1;reserve=float(np.minimum(q[23:]-f.g.w.lower[16:],f.g.w.upper[16:]-q[23:]).min())
    previous=z['object'][frame-1,env];lin=float(np.linalg.norm(o[:3]-previous[:3])*30);ang=float(np.linalg.norm((Rotation.from_quat(o[3:7])*Rotation.from_quat(previous[3:7]).inv()).as_rotvec())*30)
    foot=np.array(af['foot_in_knife_m']);slider_delta=slider-float(z['stage_slider_start'][env]);row=dict(env=int(env),frame=int(frame),age_s=(frame+1)/30,tail_distance_m=af['tail_roof_distance_m'],foot_in_knife_m=foot.tolist(),reserve_rad=reserve,linear_speed_m_s=lin,angular_speed_rad_s=ang,slider_delta_m=slider_delta,clearance_m=clear)
    rows.append(row)
  rows.sort(key=lambda x:x['tail_distance_m']);selected=rows[:3]
  feasible=[x for x in rows if x['reserve_rad']>.075 and abs(x['slider_delta_m'])<.002 and x['linear_speed_m_s']<.08 and x['angular_speed_rad_s']<.8]
  for row in selected+feasible[:1]:
   frame=row['frame'];env=row['env'];q=z['dof'][frame,env,:27,0].astype(float);o=z['object'][frame,env];af=f.assess(q,transform(o[:3],o[3:7]),float(z['dof'][frame,env,27,0]));row['full30mm_FK_error_m']=af['full30mm_FK_error_m'];row['reference_eligible']=af['reference_eligible']
  result=dict(round=round_no,safe_held_samples=counts,closest_safe_operating_foot=selected,closest_settled_closed_reserved=feasible[:1],policy_sha256=hashlib.sha256((src/'policy-before-update.pth').read_bytes()).hexdigest());results.append(result);print(json.dumps(result),flush=True)
 result=dict(results=results,scope='Archived actual physics; H checked every15frames untilfirstbad, no allframe certification/capacity/native claim. Closest minima exclude subsequent frozen or dropped states.')
 (a.output/'result.json').write_text(json.dumps(result,indent=2));record('safe_operating_contact_audit_terminal',[str(a.output/'result.json')],result,next_step='Contact progress plus true load/geometry and originalB decides continuation or distinct grasp mechanism')
if __name__=='__main__':main()
