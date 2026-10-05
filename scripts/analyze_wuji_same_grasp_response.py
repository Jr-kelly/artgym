"""Descriptive measured target response and externally measured force summaries.
Never fits contact force from joint error or labels simulation as hardware calibration.
"""
import argparse,json,numpy as np
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--samples',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[json.loads(x) for x in a.samples.read_text().splitlines()];assert rows
hardware=all(x['source']=='hardware_sdk' for x in rows);pairs=[r for r in rows if r.get('issued_target') is not None];result=dict(source='hardware_sdk' if hardware else 'saved_simulation_replay',records=len(rows),hardware_calibration_performed=False,effort_to_force_calibrated=False,position_response=[],external_force=[])
if pairs:
 q=np.array([r['measured']['values'] for r in pairs]);target=np.array([r['issued_target']['values'] for r in pairs]);names=pairs[0]['measured']['joint_names'];ts=np.array([r.get('simulation_time_s',r.get('host_after_ns',0)*1e-9) for r in pairs]);dt=float(np.median(np.diff(ts)))
 for j in range(16,20):
  dq=np.diff(q[:,j]);du=np.diff(target[:,j]);candidates=[]
  for lag in range(min(16,len(dq)//3)):
   x=du[:len(du)-lag] if lag else du;y=dq[lag:];gain=float(x@y/(x@x+1e-12));error=float(np.mean((y-gain*x)**2));candidates.append((error,lag,gain))
  err,lag,gain=min(candidates)
  result['position_response'].append(dict(joint=names[j],sample_dt_s=dt,descriptive_increment_delay_s=lag*dt,increment_gain=gain,fit_mse_rad2=err,tracking_error_mean_rad=float((target[:,j]-q[:,j]).mean()),tracking_error_max_rad=float(abs(target[:,j]-q[:,j]).max()),scope='Local recorded motion correlation, not firmware Kp or stiffness. Slow correlated trajectory and contacts prevent causal actuator identification.'))
forces=[r['external_force'] for r in rows if r.get('external_force')]
for station in ['start','middle','end']:
 for axis in ['normal','axial']:
  selected=[f for f in forces if f.get('station')==station and f.get('axis')==axis and abs(f.get('age_ns',0))<=100000000]
  if not selected:continue
  times=np.array([f['host_monotonic_ns'] for f in selected]);values=np.array([f['force_N'] for f in selected]);duration=float(np.ptp(times))*1e-9
  result['external_force'].append(dict(station=station,axis=axis,duration_s=duration,min_N=float(values.min()),mean_N=float(values.mean()),peak_N=float(values.max()),at_least_one_second=duration>=1.,original_sources=sorted(set(f['source'] for f in selected))))
result['next_hardware_measurements']='Actual right hand limits/axis/zero and firmware timing; simultaneous same-grasp start/middle/end independently aligned normal and axial samples >=1s; known .7355/1.0/1.25N rail loads and slip/displacement. No device data here means no calibration.'
a.output.write_text(json.dumps(result,indent=2))
