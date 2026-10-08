"""Plan a full-arm half-turn with free wrist translation and an acquired rigid grip.

No fixed knife/wrist centre, no finger follower or force change. Rotation keeps
knife-X gravity projection invariant; wholebody/hand must remain above table.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);f=FunctionalEntryAffordance();src=Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-wristcenter-roll-v870/simulation');z=np.load(src/'trace.npz');i=359;q=z['arm_q'][i].astype(float);hand=z['q'][i].astype(float);issued=z['applied_target'][i].astype(float);W=f.kin.forward(q);O=transform(z['object'][i,:3],z['object'][i,3:7]);C=np.linalg.inv(W)@O;F=f.g.w.forward(hand);vertices=[]
 for n,parts in f.g.meshes.items():
  for v,_ in parts:vertices.extend(v@F[n][:3,:3].T+F[n][:3,3])
 for x in KnifeGeometry(Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')).collision_parts(float(z['slider'][i])):vertices.extend(x['vertices']@C[:3,:3].T+C[:3,3])
 V=np.array(vertices);axis=-O[:3,0];rows=[dict(time_s=0.,angle_deg=0.,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())];audit=[];motor_offset=issued[:7]-q;began=time.monotonic();failure=None
 record('wholearm_translation_free_widthflip_geometry_started_v876',[str(src/'trace.npz')],dict(question='FixedcentrebodyX halfturn blockedatarmjoint7 ±1.536; freewholearmposition can shareorientationacrossotherarmjoints whilekeepinggripandgravitynormal?',scope=__doc__),next_step='Onecontinuous360pose7arm solve withfloor/limits; feasibleonlythenactualfreshwidthflip+wholegripgravitytransport')
 for angle in np.linspace(.5,180,360):
  R=Rotation.from_rotvec(axis*np.deg2rad(angle)).as_matrix()@W[:3,:3];previous=q.copy();lo=np.maximum(f.kin.lower+.07,previous-.10);hi=np.minimum(f.kin.upper-.07,previous+.10)
  def residual(v):
   T=f.kin.forward(v);floor=(V@T[:3,:3].T+T[:3,3])[:,2].min()-.75;dis=T[:3,3]-W[:3,3];return np.r_[Rotation.from_matrix(R.T@T[:3,:3]).as_rotvec()*30,dis*.12,(v-previous)*.0015,min(floor-.04,0)*20,max(np.linalg.norm(dis)-.25,0)*10]
  fit=least_squares(residual,np.clip(previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=120);q=fit.x;T=f.kin.forward(q);floor=float((V@T[:3,:3].T+T[:3,3])[:,2].min()-.75);err=float(Rotation.from_matrix(R.T@T[:3,:3]).magnitude());motor=q+motor_offset;steps=int(np.ceil(abs(motor-np.array(rows[-1]['arm_q'])).max()/.0045));steps=max(1,steps);rows.append(dict(time_s=rows[-1]['time_s']+steps/30,angle_deg=float(angle),arm_q=motor.tolist(),hand_q=issued[7:].tolist()));audit.append(dict(angle_deg=float(angle),rotation_error_rad=err,table_clearance_m=floor,wrist_displacement_m=float(np.linalg.norm(T[:3,3]-W[:3,3])),actual_joint_margin_rad=float(np.minimum(q-f.kin.lower,f.kin.upper-q).min()),motor_joint_margin_rad=float(np.minimum(motor-f.kin.lower,f.kin.upper-motor).min()),arm_q=q.tolist(),wrist_world=T.tolist()))
  if err>.001 or floor<.039 or audit[-1]['motor_joint_margin_rad']<.025:failure=audit[-1];break
 passed=len(audit)==360 and failure is None;result=dict(geometry_permits_native=passed,source=str(src),source_frame=i,rows=rows,audit=audit,failure=failure,elapsed_s=time.monotonic()-began,scope=__doc__);(a.output/'result.json').write_text(json.dumps(result,indent=2));record('wholearm_translation_free_widthflip_geometry_terminal_v876',[str(a.output/'result.json')],dict(passed=passed,poses=len(audit),duration_s=rows[-1]['time_s'],failure=failure,minimum_floor_m=min(x['table_clearance_m']for x in audit),max_wrist_translation_m=max(x['wrist_displacement_m']for x in audit)),next_step='Feasiblewholearmcourse -> samefreshnewpadpickup widthflip withcoupledgravitypreload; failure->exactgeometryno native');print(json.dumps(dict(passed=passed,poses=len(audit),duration_s=rows[-1]['time_s'],failure=failure,elapsed_s=result['elapsed_s'])),flush=True)
if __name__=='__main__':main()
