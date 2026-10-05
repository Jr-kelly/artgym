"""Read-only SDK discovery/recorder or clearly labelled saved-simulation replay.
External JSONL stream: {host_monotonic_ns, station, axis, force_N, source,
material, displacement_mm}; axis is normal OR axial, independently aligned.
No synthetic force substitution, implicit enabling or hardware motion.
"""
import argparse,json,time,inspect,hashlib
from pathlib import Path
import numpy as np
from isaacgymenvs.deploy.wuji.joint_mapping import WujiJointMapping
from isaacgymenvs.deploy.wuji.sdk_hand_api import WujiSDKHandAPI

def usb_inventory():
 out=[]
 for p in Path('/sys/bus/usb/devices').iterdir():
  if not (p/'idVendor').exists():continue
  row={'bus_path':p.name}
  for f in ['idVendor','idProduct','serial','product','manufacturer']:
   if (p/f).exists():row[f]=(p/f).read_text().strip()
  row['wuji_vid_pid_match']=row.get('idVendor')=='0483' and row.get('idProduct')=='2000';out.append(row)
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--runtime-names',type=Path,default=Path('research/contact-transfer-20261006/MAPPING-CHECK.json'));p.add_argument('--serial');p.add_argument('--seconds',type=float,default=3);p.add_argument('--external-jsonl',type=Path);p.add_argument('--replay-trial',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);names=json.loads(a.runtime_names.read_text())['runtime_names'];mapping=WujiJointMapping(names);external=[]
 if a.external_jsonl:
  external=[json.loads(s) for s in a.external_jsonl.read_text().splitlines() if s.strip()]
  for e in external:
   if e['axis'] not in ['normal','axial'] or not np.isfinite(e['force_N']) or 'host_monotonic_ns' not in e or 'source' not in e:raise ValueError('External sample must retain axis, time and source')
 status=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),movement_commands_sent=0,real_robot_ran=False,usb_inventory=usb_inventory(),device_connected=False)
 with (a.output/'samples.jsonl').open('w') as f:
  if a.replay_trial:
   z=np.load(a.replay_trial/'trace.npz');phy=json.loads((a.replay_trial/'physics.json').read_text());m=np.array(phy['hand_indices']);status['mode']='saved_simulation_replay';status['trace_sha256']=hashlib.sha256((a.replay_trial/'trace.npz').read_bytes()).hexdigest()
   for i,t in enumerate(z['time']):
    if t<16:continue
    row=dict(source='saved_simulation_replay',simulation_time_s=float(t),measured=mapping.record(z['q'][i],'saved_simulation_encoder'),issued_target=mapping.record(z['applied_target'][i,m],'saved_simulation_motor_target'),motor_torque=mapping.record(z['torque'][i,m],'saved_simulation_finite_motor','Nm'),actual_effort=None,effort_limit=None,external_force=None,rail_brake_capacity_N=float(z['solver_brake_capacity_N'][i]),capacity_is_contact_force=False)
    f.write(json.dumps(row)+'\n')
   status['samples_written']=int((z['time']>=16).sum());status['hardware_calibration_performed']=False
  else:
   import wujihandpy as w
   status.update(mode='read_only_sdk',sdk_version=w.__version__,hand_signature=str(inspect.signature(w.Hand)),sdk_read_methods={n:getattr(w.Hand,n).__doc__ for n in ['read_joint_actual_position','read_joint_lower_limit','read_joint_upper_limit','read_joint_effort_limit','read_system_time']},sdk_realtime_methods={n:getattr(w.IController,n).__doc__ for n in ['get_joint_actual_position','get_joint_actual_effort','set_joint_target_position']},sdk_public_usb_enumerator_available=any('enumer' in n for n in dir(w)),position_unit='rad',effort_unit='A filtered drive quantity; not Nm or contact force')
   if a.serial:
    robot=WujiSDKHandAPI(names,a.serial);robot.connect();status.update(device_connected=True,metadata=robot.metadata);end=time.monotonic()+a.seconds;count=0
    try:
     while time.monotonic()<end:
      if a.external_jsonl:
       # Read appended force-meter observations, preserving original axis/time/source.
       external=[json.loads(line) for line in a.external_jsonl.read_text().splitlines() if line.strip()]
       for frow in external:
        if frow.get('axis') not in ['normal','axial'] or not np.isfinite(frow['force_N']) or 'source' not in frow:raise ValueError('Invalid appended external measurement')
      now=time.monotonic_ns();e=min(external,key=lambda x:abs(x['host_monotonic_ns']-now)) if external else None
      if e is not None:e=dict(e,age_ns=now-e['host_monotonic_ns'])
      f.write(json.dumps(robot.sample(e))+'\n');f.flush();count+=1;time.sleep(1/30)
    finally:robot.disconnect()
    status['samples_written']=count
   else:status['connection_status']='No connection attempted: USB inventory retained, no exact device serial provided';status['samples_written']=0
 (a.output/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps({k:v for k,v in status.items() if k not in ['sdk_read_methods','sdk_realtime_methods']},indent=2))
if __name__=='__main__':main()
