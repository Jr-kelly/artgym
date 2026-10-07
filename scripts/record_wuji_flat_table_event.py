import datetime,json,hashlib,fcntl,os
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/flat-table-20261006'
MIRROR_ROOT=Path('/data/research/artgym-experiments-20260921/flat-table-20261006')
def _write(p,text):
 tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()));tmp.write_text(text,encoding='utf-8');os.replace(str(tmp),str(p))
def record(event,evidence,config=None,updates=None,next_step=None):
 with (D/'.record.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  return _record(event,evidence,config,updates,next_step)
def _record(event,evidence,config=None,updates=None,next_step=None):
 p=D/'STATE.json';s=json.loads(p.read_text()) if p.exists() else dict(local_root=str(R),actor_sha256='6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e',flat_table_pickup=False,continuous_pickup_to_extension=False,vision_validated=False,real_robot_ran=False,active_jobs=[])
 s.update(updates or {})
 if next_step:s['next']=next_step
 source_files=['run_g2_flat_table_demo.py','run_wuji_flat_connected.py','prepare_wuji_relaxed_prefix.py','wuji_prefix_pose_adaptation.py','wuji_direct_pickup.py','wuji_direct_route.py','g2_kinematics.py','g2_contact_geometry.py','wuji_direct_pressure_path_servo.py','wuji_direct_grip_roll_servo.py','wuji_direct_live_ring.py','wuji_direct_thumb_servo.py','run_wuji_direct_connected.py','run_wuji_direct_recorded.py','prepare_wuji_direct_actual_approach.py','plan_wuji_direct_back_support.py']
 source_files.append('wuji_direct_material_carrier.py')
 source_files.append('wuji_direct_rolling_pair_clearance.py')
 source_files.append('plan_wuji_forward_reaction_grip.py')
 source_files.append('prepare_wuji_forward_reaction_grip_path.py')
 source_files.append('plan_wuji_proximal_cap_stroke.py')
 source_files.extend(['wuji_direct_joint_path_tracking.py','time_wuji_free_thumb_path.py','prepare_wuji_base_first_thumb_path.py'])
 source_files.extend(['prepare_wuji_acquired_thumb_stroke.py','prepare_wuji_direct_sliding_stroke.py','prepare_wuji_loaded_coordinated_motor.py','plan_wuji_direct_coordinated_stroke.py'])
 e=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,evidence=evidence,config=config or {},actor_sha256=s['actor_sha256'],source_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [R/'scripts'/name for name in source_files] if f.exists()},next=s.get('next'));s['last_event']=e;_write(p,json.dumps(s,ensure_ascii=False,indent=2))
 journals=[D/'events.jsonl']
 if R==MIRROR_ROOT:journals.append(Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl'))
 for p in journals:
  with p.open('a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 marker='<!-- WUJI_FLAT_TABLE_HISTORY -->\n';header='# Wuji 完整平放桌面取刀 → 连续推动当前 Goal\n\n先读 `'+str(D/'CONTINUATION.md')+'`。\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n\n'+marker
 handoffs=[R/'WUJI_GOAL_HANDOFF.md']
 if R==MIRROR_ROOT:handoffs += [Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'),Path('/data/research/artgym-experiments-20260921/WUJI_GOAL_HANDOFF.md')]
 for p in handoffs:
  old=p.read_text(encoding='utf-8') if p.exists() else '';_write(p,header+old.split(marker,1)[-1])
 return e
