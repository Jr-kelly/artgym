"""Meaningful offline contracts: SDK permission/mapping, sent-command feedback, warmup and stop."""
import isaacgym
import json,hashlib
from pathlib import Path
import numpy as np
from scripts.wuji_rear_controller import RearController,load_bundle,ROOT
from scripts.wuji_rear_sdk_backend import SDKBackend
from isaacgymenvs.deploy.wuji.joint_mapping import WujiJointMapping
from scripts.record_wuji_rear_event import record
D=ROOT/'research/rear-sim2real-20261009';bundle=D/'bundle-deploy-v7.json';s=load_bundle(bundle);e={}
m=WujiJointMapping(s['runtime_joint_names']);v=np.arange(20)*.03;e['twenty_joint_mapping_roundtrip']=bool(np.array_equal(m.to_runtime(m.to_sdk(v)),v))
b=SDKBackend(bundle,'/data/research/artgym-experiments-20260921/contact-transfer-sdk310-venv/bin/python',fixture=True)
try:
    try:b.write(v)
    except RuntimeError as error:e['readonly_refuses_writes']='PermissionError' in str(error)
    else:raise AssertionError('Read-only backend allowed a write')
    q,_=b.read();assert np.array_equal(q,np.zeros(20))
finally:b.close()
b=SDKBackend(bundle,'/data/research/artgym-experiments-20260921/contact-transfer-sdk310-venv/bin/python',fixture=True,motion=True)
try:
    sent,_=b.write(v);q,_=b.read();e['fixture_written_targets_readback']=bool(np.array_equal(q,v) and np.array_equal(sent,v))
    b.sign=np.array([-1,1]*10);b.zero=np.linspace(-.03,.02,20);e['axis_zero_roundtrip']=bool(np.allclose(b.to_model(b.to_device(v)),v))
    e['explicit_stop_worker_ack']=b.stop()['disabled']
finally:b.close()
c=RearController(s);trace=np.load(ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/trace.npz');logs=[json.loads(l) for l in (ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/commands.jsonl').read_text().splitlines()]
rows=[r for r in logs if r['time_s']<6.6][-50:]
for r in rows:c.policy.record(np.array(r['measured_q_rad']),np.array(r['executed_action']))
q=np.asarray(rows[-1]['measured_q_rad']);c.seed_issued(np.asarray(rows[-1]['issued_target_rad']));hist=np.asarray(c.policy.history).copy();c.takeover(q);e['warmup_zero_commands_and_real_history_unchanged']=bool(c.warmup['commands_issued']==0 and np.array_equal(hist,np.asarray(c.policy.history)))
previous=c.issued.copy();raw=c.propose_push(q,0);sent=c.constrain(raw);sent[17]=previous[17] # Deliberately filter one raw coordinate before sending.
c.commit(sent);e['sent_target_memory_exact']=bool(np.array_equal(c.issued,sent) and np.allclose(c.policy.known.issued[0].cpu().numpy(),sent));expected=(sent[17]-previous[17])/.025;e['action_history_filtered_target']=bool(abs(c.last_action[17]-expected)<1e-7);c.observe(q);e['next_history_uses_committed_action']=bool(np.allclose(np.asarray(c.policy.history)[-1,20:],c.last_action))
saved=c.issued.copy();c.taken=False;c.issued=c.upper+.1;approach=c.constrain(c.upper-.05);e['current_pose_approach_no_jump']=bool((abs(approach-c.issued)<=.025+1e-10).all());c.issued=saved;c.taken=True
# The policy's exposed push signature contains no live slider/body/contact channels.
import inspect
allowed=set(inspect.signature(c.propose_push).parameters);e['legal_input_signature']=allowed=={'q','elapsed_s'}
result=dict(checks=e,passed=all(e.values()),source='offline_code_and_sdk_shaped_fixture',real_device_connected=False,real_robot_ran=False,bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),scope='Fixture mapping and position transport only; fixture does not simulate contact or prove hardware latency')
(D/'v2/SOFTWARE-VERIFICATION.json').write_text(json.dumps(result,indent=2));record('rear_software_contract_verification',[D/'v2/SOFTWARE-VERIFICATION.json'],result);print(json.dumps(result));assert result['passed']
