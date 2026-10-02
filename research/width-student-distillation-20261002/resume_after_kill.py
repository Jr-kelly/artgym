"""Restore frozen inputs after provider kill; retry incomplete jobs exactly once."""
import datetime,json,os,shlex,subprocess,sys,copy
from pathlib import Path
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_jobs import source_hash,host_tool_environment
from scripts.wuji_width_contract import sha
ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV']); env=host_tool_environment()
def remote(cmd):return subprocess.check_output(ssh+[cmd],text=True,timeout=30,env=env)
frozen=json.loads((D/'final-freeze.json').read_text()); freeze_sha=sha(D/'final-freeze.json')
assert source_hash(R)==frozen['source_sha256']
inv=remote("hostname; date -u +%FT%TZ; nvidia-smi --query-gpu=index,uuid,name,utilization.gpu,memory.used --format=csv,noheader; nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader; test ! -e /tmp/artgym-width-20261002 && echo TEMP_DIRECTORY_ABSENT")
assert 'TEMP_DIRECTORY_ABSENT' in inv
proof=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inventory=inv,provider_kill_local='2026-10-02T18:10:00+08:00',provider_kill_utc='2026-10-02T10:10:00+00:00',provider_running_seconds=14411,provider_window_hours=4,provider_average_utilization_pct=19.9461,threshold_pct=26,rule='3 H100/H200开发机',source='User supplied resource kill notification',old_remote_outputs='Temporary directory absent after restart; no original final output recoverable',accounting='Retain conservative 600+30 seconds charge for each interrupted job; do not claim precise GPU stop clock from notification alone')
(D/'PROVIDER_KILL_RECONCILIATION.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
state=json.loads((D/'STATE.json').read_text());old=[]
for j in state['unreconciled_remote_jobs']:
 p=R/'runs/width-student-distillation-20261002/jobs'/j['name']/'result.json';result=json.loads(p.read_text());old.append(copy.deepcopy(result));result.update(remote_status_unknown=False,provider_killed=True,accounting='Conservative original timeout upper bound retained after confirmed provider kill; actual allocation ended no later than restart verification',reconciliation='research/width-student-distillation-20261002/PROVIDER_KILL_RECONCILIATION.json');p.write_text(json.dumps(result,indent=2)+'\n')
(D/'PRE_RECONCILIATION_RECEIPTS.json').write_text(json.dumps(old,indent=2)+'\n')
record('provider_kill_confirmed_and_remote_reconnected',evidence='research/width-student-distillation-20261002/PROVIDER_KILL_RECONCILIATION.json',state_updates=dict(remote_inventory_verified=True,remote_additional_consumption_unknown=False,unreconciled_remote_jobs=[],final_transport_blocked=False),phase='Restoring frozen final after provider utilization kill',next='Restore identical hashed source, weights and cohorts; retry interrupted outputs under unique names')
remote('mkdir -p /tmp/artgym-width-20261002/source /tmp/artgym-width-20261002/runs')
source=['scripts','isaacgymenvs','rl_games','assets','caches','research/width-student-distillation-20261002','research/multigrasp-20260928/data','research/geometry-generalization-20261002/BASELINE_PHYSICS.json']
subprocess.run(['rsync','-aR','--exclude=__pycache__','--exclude=*.log','-e',shlex.join(ssh[:-1]),*source,'wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/source/'],cwd=R,env=env,check=True,timeout=240)
paths=[]
for v in frozen['models'].values():
 assert sha(R/v['path'])==v['sha256'];paths.append(v['path'])
for v in frozen['cohorts']:
 assert sha(R/v['states'])==v['states_sha256'] and sha(R/v['selection'])==v['selection_sha256'];paths.extend([v['states'],v['selection']])
subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*paths,'wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/'],cwd=R,env=env,check=True,timeout=240)
audit="from pathlib import Path;from scripts.wuji_width_jobs import source_hash;print(source_hash(Path('.')))"
assert remote('cd /tmp/artgym-width-20261002/source && python3 -c '+shlex.quote(audit)).strip()==frozen['source_sha256']
q=json.loads((D/'queues/frozen-final-v1.json').read_text());retry=0
for t in q['tasks']:
 assert t['status'] in ['pending','failed']
 if t['status']=='failed':
  original=t['name'];new=original+'-retry1';newout=t['output']+'-retry1';t['command'][t['command'].index('--output')+1]=newout;t.update(name=new,output=newout,retry_of=original);retry+=1
 t['status']='pending'
 for key in ['exit_code','controller_pid','gpu']:t.pop(key,None)
assert retry==8 and len(q['tasks'])==90 and sha(D/'final-freeze.json')==freeze_sha
q['recovery']='Provider killed original eight incomplete runs; scientific identities unchanged';qp=D/'queues/frozen-final-resume-v2.json';assert not qp.exists();qp.write_text(json.dumps(q,indent=2)+'\n')
record('frozen_final_inputs_restored_and_retry_queue_registered',evidence=str(qp.relative_to(R)),freeze_sha256=freeze_sha,retries=8,pending_untouched=82,next='Execute frozen90matrix on8H200; no optimization or model changes')
subprocess.run([sys.executable,'-m','scripts.wuji_width_queue','run','--queue',str(qp),'--gpus','0','1','2','3','4','5','6','7'],cwd=R,check=True)
assert all(t['status']=='complete' for t in json.loads(qp.read_text())['tasks'])
subprocess.run([sys.executable,str(D/'collect_registered_queues.py'),'--queues',str(qp),'--manifest',str(D/'FINAL_MANIFEST.json'),'--output',str(R/'runs/width-student-distillation-20261002/analysis/frozen-final-v1')],cwd=R,check=True)
record('frozen_final_matrix_independently_rescored',evidence='research/width-student-distillation-20261002/FINAL_MANIFEST.json',state_updates=dict(final_evaluation_complete=True),next='Report final capabilities and failures; deliver frozen raw evidence')
