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
 p=D/'STATE.json';s=json.loads(p.read_text(encoding='utf-8')) if p.exists() else dict(local_root=str(R),actor_sha256='6e89a2bb86ec4b94eba8db39bab54cc841594955bd971311353f5c7d2aaf6a9e',flat_table_pickup=False,continuous_pickup_to_extension=False,vision_validated=False,real_robot_ran=False,active_jobs=[])
 u=dict(updates or {})
 add=u.pop('add_active_jobs',[]);remove=set(u.pop('remove_active_jobs',[]))
 s.update(u)
 if add or remove:s['active_jobs']=list(dict.fromkeys([x for x in s.get('active_jobs',[]) if x not in remove]+list(add)))
 if next_step:s['next']=next_step
 source_files=['run_g2_flat_table_demo.py','run_wuji_flat_connected.py','prepare_wuji_relaxed_prefix.py','wuji_prefix_pose_adaptation.py','wuji_direct_pickup.py','wuji_direct_route.py','g2_kinematics.py','g2_contact_geometry.py','wuji_direct_pressure_path_servo.py','wuji_direct_grip_roll_servo.py','wuji_direct_live_ring.py','wuji_direct_thumb_servo.py','run_wuji_direct_connected.py','run_wuji_direct_recorded.py','prepare_wuji_direct_actual_approach.py','plan_wuji_direct_back_support.py']
 source_files.append('wuji_direct_material_carrier.py')
 source_files.append('wuji_direct_rolling_pair_clearance.py')
 source_files.append('plan_wuji_forward_reaction_grip.py')
 source_files.append('prepare_wuji_forward_reaction_grip_path.py')
 source_files.append('plan_wuji_proximal_cap_stroke.py')
 source_files.append('prepare_wuji_proximal_cap_acquisition.py')
 source_files.append('wuji_direct_relative_thumb_path.py')
 source_files.append('wuji_direct_relative_carrier_path.py')
 source_files.append('wuji_direct_normal_bearing_transport.py')
 source_files.append('plan_wuji_direct_functional_bearing_grip.py')
 source_files.append('plan_wuji_operating_surface_grip.py')
 source_files.append('plan_wuji_table_grip_from_operating.py')
 source_files.append('prepare_wuji_functional_table_pickup.py')
 source_files.append('wuji_direct_pickup_bearing.py')
 source_files.append('wuji_direct_primary_patch.py')
 source_files.extend(['plan_wuji_functional_initial_thumb.py','plan_wuji_functional_opposed_grip.py','plan_wuji_functional_side_rolling_grip.py'])
 source_files.extend(['prepare_wuji_functional_side_pickup.py','prepare_wuji_functional_side_palm_clearance.py','replay_wuji_retained_push.py','wuji_retained_push_skill.py','prepare_wuji_retained_entry_transition.py'])
 source_files.extend(['wuji_regrasp_learning.py','train_wuji_regrasp.py','wuji_fresh_prefix_learning.py','train_wuji_fresh_regrasp.py','audit_wuji_fresh_prefix.py','run_wuji_fresh_policy_connected.py','wuji_fresh_capacity_probe.py','wuji_fresh_checkpoint_migration.py','wuji_fresh_free_migration.py','wuji_pose_motion.py','wuji_fresh_pose_migration.py','wuji_motor_reference_preamble.py','audit_wuji_actual_entry_ranges.py','check_wuji_action_quality.py','wuji_functional_entry_affordance.py'])
 source_files.extend(['wuji_cap_contact_pivot.py','plan_wuji_cap_normal_pivot.py','plan_wuji_roof_contact_null_adjustment.py','audit_wuji_safe_operating_contact.py'])
 source_files.extend(['preflight_wuji_cap_contact_pivot.py','run_wuji_fresh_cap_pivot_probe.py','prepare_wuji_ideal_cap_pivot_capacity.py','plan_wuji_flexed_thumb_table_pinch.py','prepare_wuji_flexed_thumb_pickup.py'])
 source_files.extend(['prepare_wuji_balanced_pad_fresh_roll.py','preflight_wuji_balanced_grip_gravity_transport.py','wuji_whole_grip_gravity_transport.py','plan_wuji_widthaxis_free_wrist_flip.py'])
 source_files.extend(['prepare_wuji_free_wrist_fresh_widthflip.py','plan_wuji_fresh_thumb_roof_entry.py','plan_wuji_quarterroll_operating_grip.py'])
 source_files.extend(['plan_wuji_acquired_corner_roll.py','prepare_wuji_acquired_rolling_motor.py','plan_wuji_acquired_back_bearing.py','prepare_wuji_actual_ring_bearing.py','audit_wuji_relative_rolling.py','train_wuji_acquired_rolling.py','plan_wuji_coordinated_back_bearing.py'])
 source_files.append('prepare_wuji_coordinated_bearing_motor.py')
 source_files.extend(['prepare_wuji_contact_wrench_bearing.py','plan_wuji_cleared_static_primary_bearing.py','prepare_wuji_static_primary_bearing_motor.py','run_wuji_fresh_static_primary_bearing.py'])
 source_files.append('wuji_regrasp_contract.py')
 source_files.extend(['wuji_regrasp_reference_policy.py','prepare_wuji_retained_ring_entry.py','prepare_wuji_retained_ring_transition.py'])
 source_files.extend(['check_wuji_transition_reference.py','prepare_wuji_ownactual_ring_tail.py'])
 source_files.append('prepare_wuji_forward_initial_pinch.py')
 source_files.extend(['plan_wuji_safe_ring_acquisition.py','prepare_wuji_pinky_first_rear.py','prepare_wuji_rear_floor_arc.py'])
 source_files.extend(['wuji_direct_joint_path_tracking.py','time_wuji_free_thumb_path.py','prepare_wuji_base_first_thumb_path.py'])
 source_files.extend(['prepare_wuji_acquired_thumb_stroke.py','prepare_wuji_direct_sliding_stroke.py','prepare_wuji_loaded_coordinated_motor.py','plan_wuji_direct_coordinated_stroke.py'])
 source_files.extend(['wuji_contact_contour_course.py','wuji_measured_hold_reference.py','wuji_robot_gravity.py','optimize_wuji_regrasp_course.py','audit_wuji_planning_reset.py','plan_wuji_contact_contour_transfer.py','plan_wuji_temporary_side_bearing.py','prepare_wuji_gravity_supported_transfer.py','prepare_wuji_gravity_cradle_release.py','prepare_wuji_coupled_contour_native.py'])
 e=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,evidence=evidence,config=config or {},actor_sha256=s['actor_sha256'],source_sha256={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [R/'scripts'/name for name in source_files] if f.exists()},next=s.get('next'));s['last_event']=e;_write(p,json.dumps(s,ensure_ascii=False,indent=2))
 journals=[D/'events.jsonl']
 if R==MIRROR_ROOT:journals.append(Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl'))
 for p in journals:
  with p.open('a',encoding='utf-8') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
 marker='<!-- WUJI_FLAT_TABLE_HISTORY -->\n';header='# Wuji 完整平放桌面取刀 → 连续推动当前 Goal\n\n先读 `'+str(D/'CONTINUATION.md')+'`。\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n\n'+marker
 handoffs=[R/'WUJI_GOAL_HANDOFF.md']
 if R==MIRROR_ROOT:handoffs += [Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'),Path('/data/research/artgym-experiments-20260921/WUJI_GOAL_HANDOFF.md')]
 for p in handoffs:
  old=p.read_text(encoding='utf-8') if p.exists() else '';_write(p,header+old.split(marker,1)[-1])
 return e
