"""Known-clock wrist/object co-roll hypothesis to seat knife on side support.

Original motor targets and meshes only. Knife following the wrist is a physical
hypothesis; no attachment or state write establishes it. Actor gravity comes
from measured arm FK, and nominal grip calibration is retained rather than
using a live object pose to steer this path.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_cartesian_acquisition import plan_translation
from scripts.g2_table_collision import ArmTableCollision
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--degrees',type=float,default=20.);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert 10<=abs(a.degrees)<=30 and not a.output.exists();plan=json.loads(a.plan.read_text());acq=json.loads(a.acquisition.read_text());cal=json.loads(a.calibration.read_text());k=G2Kinematics();q0=np.array(acq['lift_q'][-1]);start=k.forward(q0);body=start@np.array(cal['object_in_wrist']);rotation=Rotation.from_rotvec(body[:3,2]*np.deg2rad(a.degrees)).as_matrix();target=start.copy();target[:3,:3]=rotation@start[:3,:3];target[:3,3]=body[:3,3]+rotation@(start[:3,3]-body[:3,3]);path,arm_audit=plan_translation(k,q0,target,2.,1/30,ArmTableCollision(.75));arm=np.array([q0]+path);u=np.linspace(0,1,len(arm));fraction=u*u*u*(10-15*u+6*u*u);hand=np.array(plan['close_q'])[None]+fraction[:,None]*(np.array(plan['post_lift_close_q'])-plan['close_q'])[None];g=DigitGeometry(max_face_axes=10000);rows=[]
 for i in np.unique(np.linspace(0,len(arm)-1,11).astype(int)):
  q=hand[i];w=k.forward(arm[i]);frames=g.w.forward(q);gaps=[r for f in FINGERS for r in g.self_gaps(q,f,certify_clearance_m=.000015)];bad=[r for r in gaps if r['gap_lower_bound_m']<.000015-1e-7];table=[]
  for name,meshes in g.meshes.items():
   m=w@frames[name]
   for v,n in meshes:
    vertices=v@m[:3,:3].T+m[:3,3];axes=np.r_[np.eye(3),n@m[:3,:3].T];projection=(vertices-[.6,-.25,.725])@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);table.append(float(np.maximum(projection.min(0)-radius,-radius-projection.max(0)).max()))
  rows.append(dict(frame=int(i),minimum_table_gap_m=min(table),uncertified_self_pairs=bad))
 passed=all(not r['uncertified_self_pairs'] and r['minimum_table_gap_m']>.0003 for r in rows);relative=np.array(cal['object_in_wrist']);gravity_before=(body[:3,:3].T@[0,0,-9.81]).tolist();gravity_expected=((rotation@body[:3,:3]).T@[0,0,-9.81]).tolist();result=dict(format='wuji-postlift-regrasp-v1',times_s=np.linspace(12,14,len(arm)).tolist(),arm_q=arm.tolist(),hand_q=hand.tolist(),object_in_wrist=cal['object_in_wrist'],slider_in_wrist=cal['slider_in_wrist'],preflight_passed=passed,arm_audit=arm_audit,sampled_geometry=rows,degrees=a.degrees,gravity_initial_knife_frame_m_s2=gravity_before,gravity_expected_corotating_knife_frame_m_s2=gravity_expected,scope=__doc__,source_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),contact_continuity_verified=False,hand_gravity='Originalrobot generalizedgravity compensation/finitePD remains; freeknife gravity physically loads side support')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['arm_q','hand_q','sampled_geometry','arm_audit']}),flush=True);assert passed,'Do not execute rejected roll path'
if __name__=='__main__':main()
