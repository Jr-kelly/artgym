"""Bounded contracts for v3. Fixtures prove software only; no mocked G2 backend."""
import isaacgym
import argparse,json,time,hashlib,subprocess,os
from pathlib import Path
import numpy as np
from scripts.wuji_rear_controller import RearController,load_bundle,ROOT
from scripts.wuji_rear_sdk_backend import SDKBackend
from scripts.wuji_rear_session import RearSession,DeadlineLoop,ExternalForceTail
from scripts.wuji_rear_field import targets,estimates,require_g2
from scripts.run_wuji_rear import assert_task_compatible,verified_field_speed
from isaacgymenvs.deploy.wuji.joint_mapping import WujiJointMapping
from scripts.g2_kinematics import G2Kinematics

def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,default=Path('research/rear-sim2real-20261009/bundle-deploy-v8.json'));p.add_argument('--sdk-python',required=True);p.add_argument('--old-commands',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();s=load_bundle(a.bundle);out=a.output;out.mkdir(parents=True,exist_ok=False);checks={}
 def rejects(name,fn,kind):
  try:fn()
  except kind:checks[name]=True
  else:raise AssertionError(name+' accepted bad state')
 m=WujiJointMapping(s['runtime_joint_names']);x=np.linspace(-.11,.31,20);g=np.array([-1.,1]*10);z=np.linspace(-.03,.04,20);d=g*x+z
 checks['named_permutation_signed_zero_roundtrip']=bool(np.allclose(g*(m.to_runtime(m.to_sdk(d))-z),x))
 rejects('bad_joint_names_rejected',lambda:WujiJointMapping(s['runtime_joint_names'][:-1]+[s['runtime_joint_names'][0]]),ValueError)
 k=G2Kinematics();q=np.array(s['arm_q_rad']);frames=k.forward(q,True);checks['G2_model_flange_mount_chain']=bool(np.allclose(frames['arm_r_end_link']@k.chain[-1][1],frames['hand_r_base_link']));checks['seven_rad_degree_roundtrip']=bool(np.allclose(np.radians(np.degrees(q)),q))
 rejects('G2_missing_interface_never_ready',lambda:require_g2({}),RuntimeError)
 initial=out/'initial.json';initial.write_text(json.dumps(dict(format='wuji-rear-initial-estimate-v1',frame='knife_body_initial',unit='mm',grasp='rear-fixed-wrist-v1',translation_mm=[1,2,3],slider_near_edge_mm=31,source='known_offline_test_not_measurement')))
 e=estimates(s,dict(initial_estimate=str(initial)));o=np.array(s['object_initial_estimate']);old=np.array(s['slider_initial_estimate']);checks['initial_coordinate_offsets_mm_chain']=bool(np.allclose(np.array(e['object_initial_estimate'])[:3,3]-o[:3,3],o[:3,:3]@np.array([.001,.002,.003])) and np.allclose(np.array(e['slider_initial_estimate'])[:3,3]-old[:3,3],o[:3,:3]@np.array([.001,.002,.004])))
 rejects('unverified_hardware_speed_refused',lambda:verified_field_speed(dict(wuji=dict(hardware_max_joint_speed_rad_s=[None]*20,speed_source=None)),s),ValueError)
 checks['verified_speed_keeps_full_dynamics']=bool(np.allclose(verified_field_speed(dict(wuji=dict(hardware_max_joint_speed_rad_s=[.8]*20,speed_source='offline_test_not_hardware')),s),.8))
 rejects('too_slow_device_not_silently_retimed',lambda:verified_field_speed(dict(wuji=dict(hardware_max_joint_speed_rad_s=[.001]*20,speed_source='offline_test')),s),ValueError)
 assert_task_compatible(s,np.full(20,-2),np.full(20,2));small_hi=np.full(20,2);small_hi[17]=.1;rejects('device_incompatible_named_pose_refused',lambda:assert_task_compatible(s,np.full(20,-2),small_hi),ValueError)
 b=SDKBackend(a.bundle,a.sdk_python,fixture=True,motion=True)
 try:
  rejects('one_writer_ownership',lambda:SDKBackend(a.bundle,a.sdk_python,fixture=True,motion=True),RuntimeError)
  sent,_=b.write(x);qr,_=b.read();checks['sdk_fixture_actual_ack_and_mapping']=bool(np.array_equal(sent,x) and np.array_equal(qr,x))
  # Inject only an opaque repeated device time into parent freshness boundary.
  orig=b.request
  def stale(op,**kw):
   v=orig(op,**kw)
   if op=='read':v['data']['device_system_time_raw']=b.previous_sample[0]
   return v
  b.request=stale;time.sleep(.025);rejects('stale_device_sample_rejected',b.read,TimeoutError);b.request=orig
  ack=b.stop();checks['stop_ack_not_physical_state']=bool(ack['disable_write_ack'] and ack['disabled_readback'] is None and 'disabled' not in ack)
 finally:b.close()
 # Deterministic missed-deadline case: not a CPU performance benchmark.
 now=[0.];sleep=[]
 def pause(t):sleep.append(t);now[0]+=t
 loop=DeadlineLoop(lambda:now[0],pause);loop.tick();now[0]=.02;loop.tick();now[0]=.101
 rejects('missed_deadline_no_burst',loop.tick,TimeoutError);checks['no_catchup_sample_gap']=all(v>=0 for v in sleep) and loop.last_gap>=1/30
 force=out/'force.jsonl';force.write_text(json.dumps(dict(axis='normal',force_N=.1,host_monotonic_ns=time.monotonic_ns(),source='offline_test'))+'\n');tail=ExternalForceTail(force);v=tail.sample();offset=tail.offset;tail.sample();checks['incremental_force_read_not_rescan']=tail.offset==offset and v['force_N']==.1
 # Real frozen model loads; exact saved legal encoder/issued history, no sim truth inputs.
 c=RearController(s);c.seed_issued(s['open_q_rad']);session=RearSession(c)
 rejects('loaded_restart_cannot_open',session.begin_open,RuntimeError);session.confirm_empty();session.begin_open();session.placed();errs=[];beg=time.perf_counter();release=False;take=None;first=None
 rows=[json.loads(l) for l in a.old_commands.read_text().splitlines()];push=s['release_seconds']+s['settle_seconds']
 for r in rows:
  t=r['time_s'];measured=np.array(r['measured_q_rad'])
  if not release and t>=s['release_seconds']:session.unsupported();release=True
  c.observe(measured)
  if t<s['prepare_seconds']:raw=session.target('close',measured,t)
  elif t<push:
   if t>=s['release_seconds']+s['prewarm_after_release_seconds'] and not c.taken:
    session.prepare_push('push');before=np.array(c.policy.history).copy();c.takeover(measured);checks['warmup_preserves_real_history_zero_writes']=bool(np.array_equal(before,np.array(c.policy.history)) and c.warmup['commands_issued']==0);take=c.issued.copy()
   raw=c.propose_hold(s['hold_target_rad'])
  else:raw=session.target('push',measured,t-push)
  sent=c.constrain(raw);c.commit(sent)
  if t>=push and first is None:first=sent.copy()
  errs.append(float(np.max(abs(sent-np.array(r['issued_target_rad'])))))
 checks['full_380_commands_parity']=max(errs)<2e-6
 checks['takeover_first_target_bounded']=float(np.max(abs(first-take)))<=.0250001
 session.push_done();rejects('probe_changed_initial_state_cannot_push_again',lambda:session.prepare_push('push'),RuntimeError);rejects('loaded_end_cannot_auto_open',session.begin_open,RuntimeError);session.wait_unload();session.unloaded();session.begin_open();checks['explicit_unload_required_before_reopen']=session.state=='waiting_placement'
 result=dict(checks=checks,passed=all(checks.values()),bundle_sha256=hashlib.sha256(a.bundle.read_bytes()).hexdigest(),command_frames=len(rows),maximum_command_error_rad=max(errs),wall_seconds=time.perf_counter()-beg,inference=c.summary(),source='offline_actual_models_saved_legal_inputs_and_SDK_fixture',g2_interface_verified=False,real_robot_ran=False)
 (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));assert result['passed']
if __name__=='__main__':main()
