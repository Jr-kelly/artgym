"""Short actual-state development runner, never a full-route acceptance."""
import argparse,json,subprocess,sys
from pathlib import Path
from scripts.record_wuji_flat_table_event import record
import hashlib, shutil
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--motor',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,required=True);p.add_argument('--uncertainty',required=True);p.add_argument('--decision',required=True);p.add_argument('--close-camera-direction',type=float,nargs=3,default=[.05,-.35,.65]);p.add_argument('--support-camera-direction',type=float,nargs=3);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
motor_metadata=json.loads(a.motor.read_text())
required= motor_metadata.get('required_actual_source')
if required is not None and Path(required).resolve()!=a.source.resolve():
 raise ValueError('Motor controller requires a different actual grasp source')
runtime=a.output/'controller-source';runtime.mkdir()
source_hashes={}
for name in ['run_g2_flat_table_demo.py','g2_contact_geometry.py','g2_kinematics.py','wuji_direct_route.py','wuji_direct_pickup.py','wuji_direct_live_ring.py','wuji_direct_grip_roll_servo.py','wuji_direct_primary_patch.py','wuji_retained_push_skill.py','g2_r800_policy.py','wuji_joint_deflection_pressure.py','wuji_scheduled_thumb_reference.py','wuji_known_controller.py','wuji_regrasp_reference_policy.py','wuji_regrasp_learning.py','train_wuji_regrasp.py','wuji_regrasp_contract.py']:
 source=Path(__file__).resolve().parent/name
 shutil.copyfile(source,runtime/name)
 source_hashes[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
(runtime/'manifest.json').write_text(json.dumps(dict(source_sha256=source_hashes,actual_source=str(a.source),motor_sha256=hashlib.sha256(a.motor.read_bytes()).hexdigest(),scope='Controller source snapshot only; actual-state development still lacks exact robot velocity/contact cache'),indent=2))
c=json.load(open('runs/flat-table-20261006/direct/development/center-load-feedback-v8/command.json'));c[0]=sys.executable
i=c.index('--flat-table-prefix');del c[i:i+2]
c[c.index('--seconds')+1]=str(a.seconds);c[c.index('--output')+1]=str(a.output/'simulation');c+=['--recorded-handoff',str(a.source),'--recorded-support-command',str(a.motor),'--close-camera-direction']+[str(x) for x in a.close_camera_direction]
if a.support_camera_direction:c+=['--support-camera-direction']+[str(x) for x in a.support_camera_direction]
(a.output/'command.json').write_text(json.dumps(c,indent=2));record('direct_recorded_native_start',[str(a.output/'command.json'),str(a.motor)],config={'uncertainty':a.uncertainty,'decision':a.decision,'seconds':a.seconds,'scope':'Short actualstate development; missing exactrobotvelocity/contactcache; no final acceptance'},updates={'add_active_jobs':[str(a.output)]},next_step=a.decision)
try:subprocess.run(c,check=True)
finally:record('direct_recorded_native_terminal',[str(a.output/'simulation')],updates={'remove_active_jobs':[str(a.output)]},next_step='Read actual contacts and first divergence, advance changed mechanism without fullpickup rerun')
