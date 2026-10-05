"""Predeclared relative-initial two-cycle35mm task. Historical score kept separate."""
import argparse,json,hashlib,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
from scripts.evaluate_wuji_antirotation import evaluate as old_evaluate
R=Path(__file__).resolve().parents[1]
def evaluate(trial):
 trace=np.load(trial/'trace.npz');t=trace['time'];q=trace['slider'];report=json.loads((trial/'report.json').read_text());initial=report['initial_slider_q_m'];q=q-initial
 old=old_evaluate(trial);(trial/'historical-functional-evaluation.json').write_text(json.dumps(old,indent=2))
 def at(end):
  ids=np.flatnonzero((t>end-1)&(t<=end+.001));return float(np.median(q[ids])) if len(ids) else None
 ends=[at(x) for x in [21,26,31,36]];starts=[at(16),at(26)];forward=[ends[i*2]-starts[i] for i in range(2)];returns=[ends[i*2+1]-ends[i*2] for i in range(2)]
 asset=Path(report['physical_asset']);asset=asset if asset.is_absolute() else R/asset;limit=E.parse(asset).find('./joint/limit');lo=float(limit.get('lower'))-initial;hi=float(limit.get('upper'))-initial;op=t>=16
 hold_ranges=[float(np.ptp(q[(t>end-1)&(t<=end+.001)])) for end in [21,26,31,36]]
 checks={k:v for k,v in old['checks'].items() if k!='endpoints'}
 checks.update(holds=all(x<=.002 for x in hold_ranges),continuous_pickup=bool(report['lifted_clear'] and not old['held_diagnostic']),forward_travel=all(x>=.030 for x in forward),extension_position=all(.030<=ends[i]<=.040 for i in [0,2]),return_residual=all(abs(ends[i])<=.005 for i in [1,3]),no_endstop=bool(np.min(q[op]-lo)>.002 and np.min(hi-q[op])>.002),complete_duration=bool(t[-1]>=35.99))
 params=json.loads((asset.parent/'parameters.json').read_text());capwidth=params['slider_size'][0];bodytop=params['handle_size'][1]/2
 effective=[]
 for line in (trial/'wrap-contact-physical-steps.jsonl').open():
  row=json.loads(line)
  if row['time_s']>=16:
   effective.append(any('thumb' in c['hand_link'] and c['knife_link']=='link_1' and c['position_knife_m'][1]>=bodytop-.0002 and abs(c['position_knife_m'][0])<=capwidth/2+.0002 and c['normal_magnitude_N']>1e-6 for c in row['contacts']))
 longest=span=0
 for contact in effective:span=0 if contact else span+1;longest=max(longest,span)
 checks['effective_cap_contact']=bool(effective and np.mean(effective)>=.90 and longest/240<=.5)
 result=dict(effective_cap_contact_fraction=float(np.mean(effective)) if effective else 0.,effective_cap_longest_loss_s=longest/240,version='newknife-functional-v1',checks=checks,pass_all=all(checks.values()),endpoints_relative_initial_m=ends,forward_displacement_m=forward,retract_displacement_m=returns,forward_start_m=starts,hold_slider_ranges_m=hold_ranges,old_checks=old['checks'],old_rotation_rad=old['relative_max_rotation_rad'],thumb_contact_fraction=old['thumb_contact_substep_fraction'],trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),scope='Simulation only; return to task initial, not proven hidden blade; legacy lower-stop score reported separately')
 (trial/'newknife-evaluation.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();print(json.dumps(evaluate(a.trial),indent=2))
