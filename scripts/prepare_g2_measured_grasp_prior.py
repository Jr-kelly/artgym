"""Offline operation geometry from an actual continuous pickup, never live feedback.

The emitted operation plan must not replace the certified pickup motor plan:
its frame and touch joints describe the already held physical knife.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform


def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--knife-asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--time',type=float,default=15.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    z=np.load(a.trace);i=int(np.argmin(abs(z['time']-a.time)));assert 12<=z['time'][i]<16
    world=transform(z['object'][i,:3],z['object'][i,3:7]);wrist=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);relative=np.linalg.inv(wrist)@world
    parameters=json.loads((a.knife_asset.parent/'parameters.json').read_text());center=np.array(parameters['slider_origin']);center[2]+=float(z['slider'][i]);slider=relative@transform(center)
    calibration=dict(object_in_wrist=relative.tolist(),slider_in_wrist=slider.tolist(),source_trace=str(a.trace),source_trace_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),sample_time_s=float(z['time'][i]),scope='Once-loaded offline prior from actual TABLE pickup; same calibration for all subsequent physical assets, no live object/slider feedback',physical_asset=str(a.knife_asset),slider_at_calibration_m=float(z['slider'][i]))
    plan=json.loads(a.plan.read_text());plan.update(wrist_in_knife=np.linalg.inv(relative).tolist(),touch_q=z['q'][i].tolist(),planning_slider_m=float(z['slider'][i]),offline_measured_operation_only=True,measured_prior=calibration)
    (a.output/'calibration.json').write_text(json.dumps(calibration,indent=2));(a.output/'operation-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(sample_time_s=float(z['time'][i]),measured_thumb_q=z['q'][i,16:].tolist(),scope=calibration['scope'])))


if __name__=='__main__':main()
