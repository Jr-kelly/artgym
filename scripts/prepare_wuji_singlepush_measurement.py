"""Nonmoving force-measurement preparation and optional strictly read-only SDK probe."""
import argparse,datetime,json,importlib.util,csv
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--trajectory-audit',type=Path,required=True);p.add_argument('--read-device',action='store_true');p.add_argument('--serial');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);audit=json.loads(a.trajectory_audit.read_text());status=dict(sdk_installed=importlib.util.find_spec('wujihandpy') is not None,usb_candidates=[str(p) for p in Path('/dev').glob('ttyACM*')],movement_commands_sent=0,hardware_verified=False,real_robot_ran=False)
 if a.read_device:
  assert a.serial,'Read-only probe needs an exact device serial, never selects an unknown robot'
  import wujihandpy
  hand=wujihandpy.Hand(serial_number=a.serial);status['device']={name:getattr(hand,'read_'+name)() for name in ['firmware_version','firmware_date','handedness']};status['device'].update({name:getattr(hand,'read_'+name)().tolist() for name in ['joint_actual_position','joint_lower_limit','joint_upper_limit','joint_effort_limit']});status['actual_effort_A']=None;status['actual_effort_reason']='Only available through realtime controller API; this probe does not start control or enable joints'
 (a.output/'device-status.json').write_text(json.dumps(status,indent=2));(a.output/'poses.json').write_text(json.dumps(audit['measurement_pose_samples'],indent=2))
 fields=['station','axis','known_load_N','duration_s','measured_force_N','force_min_N','force_mean_N','force_peak_N','hand_measured_rad','hand_commanded_rad','effort_A','device_firmware','effort_limit_A','notes']
 with (a.output/'force-log-template.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for station in ['start','middle','end']:
   for axis in ['normal','axial']:
    for load in [.73549875,1.,1.25,1.5]:w.writerow(dict(station=station,axis=axis,known_load_N=load,duration_s=1,notes='Unexecuted. Force axis must be independently aligned, not mixed scale reading.'))
 print(json.dumps(status))
if __name__=='__main__':main()
