"""Evaluation only: wrist-relative slip, cycle endpoints and settling.
All thresholds are declared before new physical rollouts, not fitted to old angles.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

CRITERION=dict(version=1,declared_utc='2026-10-03T20:22:00+00:00',
 scope='Functional two-cycle behavior, separately from unchanged historical 0.25rad world-pose regression; diagnostic held resets never qualify as pickup demos.',
 endpoint=dict(extension_min_m=.025,retraction_max_m=.008,command_travel_m=.04),
 grip=dict(minimum_height_above_table_m=.03,relative_translation_envelope_m=.015,
 relative_rotation_envelope_rad=.6,cycle_return_translation_increment_max_m=.005,
 cycle_return_rotation_increment_max_rad=.10,final_hold_translation_speed_max_m_s=.003,
 final_hold_rotation_speed_max_rad_s=.06),
 contact=dict(thumb_slider_substep_fraction_min=.90,maximum_contiguous_zero_contact_s=.5),
 rationale='15mm and 0.6rad are broad escape envelopes, not precision targets. Return-to-return drift <=5mm/0.10rad and last-second settling distinguish progressive slip from bounded new seating; both meaningful endpoints and sustained slider contact remain mandatory. World-pose legacy score is reported unchanged; active wrist motion is shown separately.')

def evaluate(trial,table_height=.75):
 t=np.load(trial/'trace.npz');clock=t['time'];report=json.loads((trial/'report.json').read_text()) if (trial/'report.json').exists() else {};mask=clock>=16;ids=np.flatnonzero(mask)
 if not len(ids):return dict(functional_behavior_pass=False,reason='No operation samples',criterion=CRITERION)
 wr=Rotation.from_quat(t['wrist'][:,3:7]);ob=Rotation.from_quat(t['object'][:,3:7]);rel=wr.inv()*ob
 rel_p=wr.inv().apply(t['object'][:,:3]-t['wrist'][:,:3]);origin=max(0,ids[0]-1);err=rel[origin].inv()*rel;rv=err.as_rotvec();dp=np.linalg.norm(rel_p-rel_p[origin],axis=1);angle=err.magnitude();wrist=(wr[origin].inv()*wr).magnitude()
 def endpoint(end):
  idx=np.flatnonzero((clock>end-1)&(clock<=end+.001));return int(idx[-1]),float(np.median(t['slider'][idx]))
 # Slider lower endpoint is authored in asset and must not be inferred from run minima.
 plan=json.loads((trial/'plan.json').read_text());asset=Path(report.get('physical_asset','assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf'))
 import xml.etree.ElementTree as ET
 if not asset.is_absolute():asset=Path(__file__).resolve().parents[1]/asset
 # Portability only: remote absolute paths retain their repository-relative suffix.
 if not asset.exists():
  for marker in ['/runs/','/assets/']:
   if marker in str(asset):
    local=Path(__file__).resolve().parents[1]/(marker.strip('/')+'/'+str(asset).split(marker,1)[1])
    if local.exists():asset=local;break
 lower=float(ET.parse(asset).find('.//joint[@type="prismatic"]/limit').get('lower'))
 ends={};indices={}
 for label,at in [('extend1',21),('return1',26),('extend2',31),('return2',36)]:
  if clock[-1]>=at-.1:i,s=endpoint(at);indices[label]=i;ends[label]=s-lower
 complete=len(ends)==4
 pressure=t['pair_slider_contact_substep_fraction'][:,0] if 'pair_slider_contact_substep_fraction' in t else (t['finger_slider_contacts'][:,0]>0).astype(float)
 lost=pressure[mask]<=0;longest=run=0
 for v in lost:run=run+1 if v else 0;longest=max(longest,run)
 final=np.flatnonzero((clock>35)&(clock<=36.001));return_drift=return_rot=None;speed_p=speed_r=None
 if complete:
  i,j=indices['return1'],indices['return2'];return_drift=float(np.linalg.norm(rel_p[j]-rel_p[i]));return_rot=float((rel[i].inv()*rel[j]).magnitude())
 if len(final)>1:
  delta=clock[final[-1]]-clock[final[0]];speed_p=float(np.linalg.norm(rel_p[final[-1]]-rel_p[final[0]])/delta);speed_r=float((rel[final[0]].inv()*rel[final[-1]]).magnitude()/delta)
 g=CRITERION['grip'];checks=dict(two_cycles=complete,
  clear=bool(np.min(t['object'][mask,2])>table_height+g['minimum_height_above_table_m']),
  relative_envelope=bool(dp[mask].max()<g['relative_translation_envelope_m'] and angle[mask].max()<g['relative_rotation_envelope_rad']),
  endpoints=bool(complete and ends['extend1']>.025 and ends['extend2']>.025 and ends['return1']<.008 and ends['return2']<.008),
  bounded_return_drift=bool(complete and return_drift<.005 and return_rot<.10),
  final_settling=bool(speed_p is not None and speed_p<.003 and speed_r<.06),
  thumb_contact=bool(pressure[mask].mean()>=.90 and longest/30<=.5))
 held=bool(plan.get('args',{}).get('held_diagnostic',False));measurement=bool(plan.get('args',{}).get('serial_load_cell_diagnostic',False));result=dict(criterion=CRITERION,trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),checks=checks,functional_behavior_pass=all(checks.values()),continuous_pickup_demo_pass=bool(all(checks.values()) and not held and not measurement and report.get('lifted_clear',False)),held_diagnostic=held,measurement_diagnostic=measurement,legacy_full_success=report.get('full_success'),slider_endpoints_m=ends,relative_max_rotation_rad=float(angle[mask].max()),relative_max_translation_m=float(dp[mask].max()),active_wrist_max_rotation_rad=float(wrist[mask].max()),return_to_return_rotation_rad=return_rot,return_to_return_translation_m=return_drift,final_hold_translation_speed_m_s=speed_p,final_hold_rotation_speed_rad_s=speed_r,thumb_contact_substep_fraction=float(pressure[mask].mean()),longest_zero_thumb_contact_s=longest/30)
 np.savez_compressed(trial/'relative-hand-evaluation.npz',time=clock,relative_rotvec_rad=rv,relative_translation_m=rel_p-rel_p[origin],active_wrist_rotation_rad=wrist)
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path);p.add_argument('--declare',type=Path);a=p.parse_args()
 if a.declare:a.declare.write_text(json.dumps(CRITERION,indent=2)+'\n')
 if a.trial:
  result=evaluate(a.trial);(a.trial/'functional-evaluation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
