"""Known thumb seating correction on a physically retaining postlift transfer.

Uses a fixed prior calibrated in an earlier episode, never live object pose.
Retains arm and support motor paths; screens original full-mesh self/table and
velocity limits before any free-knife physics. Geometry is not force control.
"""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--path',type=Path,required=True);p.add_argument('--registered-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();j=json.loads(a.path.read_text());plan=json.loads(a.registered_plan.read_text());assert j['preflight_passed'] and plan['thumb_registration_audit']['geometry_passed'];q=np.array(j['hand_q']);times=np.array(j['times_s']);start=q[0,16:].copy();goal=np.array(plan['close_q'][16:]);u=np.clip((times-times[0])/(times[-1]-times[0]),0,1);f=u*u*u*(10-15*u+6*u*u);q[:,16:]=start[None]+f[:,None]*(goal-start)[None];g=DigitGeometry();h=g.w;k=G2Kinematics();root=Path(__file__).resolve().parents[1];xml=ET.parse(root/h.config['asset']);limits={z.get('name'):float(z.find('limit').get('velocity')) for z in xml.findall('joint') if z.get('type')=='revolute'};rate=abs(np.diff(q,axis=0))/np.diff(times)[:,None];velocity_ok=bool(np.all(rate<np.array([limits[n] for n in h.names])[None]));rows=[]
 for i in np.unique(np.linspace(0,len(q)-1,23).astype(int)):
  gaps=[z for f in ['thumb','index','middle','ring','pinky'] for z in g.self_gaps(q[i],f,certify_clearance_m=.000015)];bad=[z for z in gaps if z['gap_lower_bound_m']<.000015-1e-7];w=k.forward(np.array(j['arm_q'][i]));fk=h.forward(q[i]);table=[]
  for name,meshes in g.meshes.items():
   m=w@fk[name]
   for v,n in meshes:
    vv=v@m[:3,:3].T+m[:3,3];axes=np.r_[np.eye(3),n@m[:3,:3].T];projection=(vv-[.6,-.25,.725])@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);table.append(float(np.maximum(projection.min(0)-radius,-radius-projection.max(0)).max()))
  rows.append(dict(frame=int(i),uncertified_self_pairs=bad,minimum_table_gap_m=min(table)))
 passed=bool(velocity_ok and np.all(q>h.lower) and np.all(q<h.upper) and all(not r['uncertified_self_pairs'] and r['minimum_table_gap_m']>.0003 for r in rows));relative=np.linalg.inv(np.array(plan['wrist_in_knife']));slider=relative.copy();slider[:3,3]+=relative[:3,:3]@np.array([0,.0075,-.02205]);j.update(hand_q=q.tolist(),object_in_wrist=relative.tolist(),slider_in_wrist=slider.tolist(),preflight_passed=passed,closed_thumb_preparation=dict(scope=__doc__,registered_plan=str(a.registered_plan),original_velocity_limits_passed=velocity_ok,maximum_thumb_motor_rate_rad_s=float(rate[:,16:].max()),samples=rows,contact_continuity_verified=False));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(dict(passed=passed,velocity_ok=velocity_ok,bad_pairs=sum(len(r['uncertified_self_pairs']) for r in rows))));assert passed,'Do not execute rejected thumb seating path'
if __name__=='__main__':main()
