"""Jointly unload underside preload and withdraw side clamp after upward wrist alignment.

Actual recorded motor/positions only. Gravity, original PD and geometry unchanged.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(Path(a.source)/'takeover.npz');q=z['robot_q'].astype(float);issued=z['issued_target'].astype(float);g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@G2Kinematics().forward(q[:7]);H=HandIntersection();end=np.array([.99448,.33617,-.008086,-.07873]);rows=[];audit=[]
 for tick in range(76):
  t=tick/30;u=np.clip((t-.5)/1.4,0,1);f=10*u**3-15*u**4+6*u**5;hand=q[7:].copy();hand[16:]=(1-f)*q[23:]+f*end;gaps=g.gaps(hand,L,float(z['slider_q']),'thumb',certify_clearance_m=.0001);bad=H.inspect(hand);audit.append({'t':t,'minimum_thumb_knife_gap_m':min(r['gap_lower_bound_m'] for r in gaps),'self':bad});motor=issued.copy();load=np.clip(t/.5,0,1);motor[7:23]=issued[7:23]*(1-load)+q[7:23]*load;motor[23:]=hand[16:]+(issued[23:]-q[23:])*(1-f)
  if rows:
   prev=np.array(rows[-1]['arm_q']+rows[-1]['hand_q']);motor=np.clip(motor,prev-np.r_[[.006]*7,[.025]*20],prev+np.r_[[.006]*7,[.025]*20])
  rows.append({'time_s':t,'arm_q':motor[:7].tolist(),'hand_q':motor[7:].tolist()})
 report={'scope':__doc__,'minimum_thumb_gap_m':min(r['minimum_thumb_knife_gap_m'] for r in audit),'self_geometry_frames':sum(bool(r['self']) for r in audit),'rows':audit};(a.output/'geometry.json').write_text(json.dumps(report,indent=2));out={'required_actual_source':a.source,'rows':rows,'development_abort_on_translation_m':.08,'scope':__doc__};(a.output/'motor.json').write_text(json.dumps(out,indent=2));record('gravity_cradle_release_prepared',[str(a.output/'geometry.json'),str(a.output/'motor.json')],{k:v for k,v in report.items() if k!='rows'},next_step='Native gravitycradle independence beforecap arrival; fail->choose earlier realbearing or revise grip, no scalarpressure scan');print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
if __name__=='__main__':main()
