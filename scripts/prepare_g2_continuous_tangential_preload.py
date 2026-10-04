"""Stage real index formation then a collision-screened thumb preparation."""
import argparse,json,copy,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def smooth(u):u=np.clip(u,0,1);return u**3*(10-15*u+6*u*u)
def main():
 p=argparse.ArgumentParser();p.add_argument('--preparation',type=Path,required=True);p.add_argument('--pickup-plan',type=Path,required=True);p.add_argument('--roll-path',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();prep=json.loads(a.preparation.read_text());assert prep['all_feasible'];old=json.loads(a.pickup_plan.read_text());roll=json.loads(a.roll_path.read_text());assert roll['preflight_passed'];times=np.linspace(12,14.2,67);rt=np.array(roll['times_s']);ra=np.array(roll['arm_q']);arm=np.stack([np.interp(times,rt,ra[:,i]) for i in range(7)],-1);q0=np.array(old['close_q']);q1=np.array(old['post_lift_close_q']);hand=q0[None]+smooth((times-12)/1.2)[:,None]*(q1-q0)[None];rows=prep['preparation_rows'];virtual=np.array([r['virtual_shift_m'] for r in rows])[::-1];thumb=np.array([r['q_thumb'] for r in rows])[::-1];lead=abs(virtual[0]);shift=-lead*smooth((times-13.2)/1.0)
 for j in range(4):hand[:,16+j]=np.interp(shift,virtual,thumb[:,j])
 g=DigitGeometry(max_face_axes=10000);k=G2Kinematics();audits=[]
 for i in np.unique(np.linspace(0,len(times)-1,23).astype(int)):
  q=hand[i];w=k.forward(arm[i]);frames=g.w.forward(q);bad=[r for f in FINGERS for r in g.self_gaps(q,f,certify_clearance_m=.000015) if r['gap_lower_bound_m']<.000015-1e-7];table=[]
  for name,meshes in g.meshes.items():
   m=w@frames[name]
   for v,n in meshes:
    verts=v@m[:3,:3].T+m[:3,3];axes=np.r_[np.eye(3),n@m[:3,:3].T];projection=(verts-[.6,-.25,.725])@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);table.append(float(np.maximum(projection.min(0)-radius,-radius-projection.max(0)).max()))
  audits.append(dict(frame=int(i),time_s=float(times[i]),minimum_table_gap_m=min(table),uncertified_self_pairs=bad))
 root=Path(__file__).resolve().parents[1];robot=ET.parse(root/g.w.config['asset']);vel={j.get('name'):float(j.find('limit').get('velocity')) for j in robot.findall('joint') if j.get('type')=='revolute'};rates=np.max(abs(np.diff(hand,axis=0)),axis=0)*30;limits=np.array([vel[name] for name in g.w.names]);rate_ok=bool(np.all(rates<=limits));passed=rate_ok and all(not r['uncertified_self_pairs'] and r['minimum_table_gap_m']>.0003 for r in audits);path=copy.deepcopy(roll);path.update(times_s=times.tolist(),arm_q=arm.tolist(),hand_q=hand.tolist(),preflight_passed=passed,sampled_geometry=audits,maximum_hand_command_rates_rad_s=rates.tolist(),hand_original_velocity_limits_passed=rate_ok,closed_tangential_prepare_m=lead,scope='Actualmotor-only pickup, indexformation12--13.2s, thumbtangential preparation13.2--14.2s and existing20deg wrist co-roll12--14s; no object reset/historyclear/force feedback. Leaves54 constant actualhistoryframes before16s. Rail externalcommand40mm, virtualmotor46mm.')
 plan=copy.deepcopy(old);plan.update(post_lift_close_q=hand[-1].tolist(),post_lift_preload_seconds=[12,14.2],post_lift_preparation_scope=path['scope']);a.output.mkdir(parents=True,exist_ok=False)
 for name,value in [('postlift-path.json',path),('motor-plan.json',plan),('reference.json',prep['reference'])]:(a.output/name).write_text(json.dumps(value,indent=2))
 print(json.dumps(dict(preflight_passed=passed,minimum_table_gap_m=min(r['minimum_table_gap_m'] for r in audits),uncertified_samples=sum(bool(r['uncertified_self_pairs']) for r in audits),maximum_hand_rate_rad_s=float(rates.max()),rate_ok=rate_ok)),flush=True);assert passed,'Reject continuous thumb preparation before physics'
if __name__=='__main__':main()
