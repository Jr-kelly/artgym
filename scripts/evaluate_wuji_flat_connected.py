"""Whole-flat origin and independent native air-held active extension checks."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts.evaluate_wuji_singlepush import evaluate
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.g2_kinematics import transform

def run(trial):
 result=evaluate(trial);z=np.load(trial/'trace.npz');r=json.load(open(trial/'report.json'));p=r.get('flat_table_prefix',{});asset=r['physical_asset'];spec=trial/'evaluated-geometry.json';spec.write_text(json.dumps(dict(asset_urdf=asset,file_sha256={})));g=KnifeGeometry(spec);op=z['time']>=16;clear=[]
 for i in np.flatnonzero(op):
  O=transform(z['object'][i,:3],z['object'][i,3:7]);V=np.concatenate([c['vertices'] for c in g.collision_parts(float(z['slider'][i]))]);clear.append(float((V@O[:3,:3].T+O[:3,3])[:,2].min()-.75))
 first=transform(z['object'][0,:3],z['object'][0,3:7]);V=np.concatenate([c['vertices'] for c in g.collision_parts(float(z['slider'][0]))]);world=V@first[:3,:3].T+first[:3,3];flat=abs(first[2,1])>.999 and world[:,2].min()>=.749 and np.all(world[:,0]>=.299) and np.all(world[:,0]<=.901) and np.all(world[:,1]>=-.631) and np.all(world[:,1]<=.171)
 table=0;support=True
 for line in (trial/'wrap-contact-physical-steps.jsonl').open():
  row=json.loads(line)
  if row['time_s']>=16:
   table+=sum('table' in [c.get('body0'),c.get('body1'),c.get('hand_link')] for c in row['contacts']);support &= any('thumb' not in c['hand_link'] and c['normal_magnitude_N']>1e-6 for c in row['contacts'])
 # Complete scene pair log includes table contacts even though wrap stream is hand-only.
 for line in (trial/'knife-contact-pairs.jsonl').open():
  row=json.loads(line)
  if row['time_s']>=16 and 'table' in [row['body0'],row['body1']]:table+=1
 physics=json.load(open(trial/'physics.json'));recorded=(trial/'recorded-initialization.json').exists()
 checks=dict(fullflat_motor_prefix=bool(p and flat and not recorded),no_stage_reset=bool(physics['initial_state_writes_only'] and p.get('physical_state_resets_after_initialization')==0),whole_knife_clear=bool(clear and min(clear)>.02),native_table_absent=table==0,nonthumb_support_every_physical_frame=support,existing_B_extension=result['pass_all'])
 out=dict(checks=checks,pass_all=all(checks.values()),active_forward_m=result['active_forward_m'],prepush_slider_m=result['prepush_slider_m'],hold_min_active_m=result['hold_min_active_m'],hold_range_m=result['hold_range_m'],min_whole_clearance_m=min(clear),table_records_during_push=table,prefix_duration_s=p.get('stage_clock_offset_s'),total_elapsed_s=float(z['time'][-1]-z['time'][0]),initial_object=z['object'][0].tolist(),pose_source='sim_oracle or explicit pose input; see postpush-pose-update.json',actual_total_axial_contact_force_N=None,simulation_only=True,real_robot_ran=False,trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest())
 (trial/'connected-evaluation.json').write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.trial)))
