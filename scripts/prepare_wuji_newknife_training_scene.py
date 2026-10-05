"""Reuse certified actual postlift motor history in bounded continuous training."""
import argparse,json,hashlib,copy
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--operation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
 base=json.loads(Path('runs/newknife-20261005/batch/config/scene.json').read_text());transfer=json.loads((a.operation/'postlift-transfer.json').read_text());ref=json.loads((a.operation/'reference.json').read_text());assert transfer['preflight_passed'] and max(r['max_active_point_error_m'] for r in transfer['contact_point_tracking'])<.001
 audit=json.loads((a.operation/'actual-transfer-stroke-audit.json').read_text());assert audit['all_passed'] and not audit['rate_limit_required']
 cal={k:transfer[k] for k in ['object_in_wrist','slider_in_wrist']};base.update(postlift_regrasp=transfer,calibration=cal,support_waypoint_interpolation='linear',operation_geometry_sha256={f:hashlib.sha256((a.operation/f).read_bytes()).hexdigest() for f in ['postlift-transfer.json','reference.json']})
 for row in base['initial_estimated_plans']:
  row.update(calibration=cal,thumb_reference=ref,support_target_q=transfer['hand_q'][-1],support_motor_waypoints=[dict(time_s=t,q=q) for t,q in zip(transfer['times_s'],transfer['hand_q'])])
 for profile in ['constant','variable']:
  scene=copy.deepcopy(base);scene['newknife_resistance']=json.loads(Path('research/newknife-20261005/resistance-'+profile+'.json').read_text());(a.output/('scene-'+profile+'.json')).write_text(json.dumps(scene,indent=2))
 print(json.dumps(base['operation_geometry_sha256']))
if __name__=='__main__':main()
