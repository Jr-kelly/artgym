"""Rescore new completed checkpoint conditions every five minutes."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
root=Path("/home/wangjiarui/artgym-experiments-20260921");g=root/'runs/wuji-goal';d=g/'diagnostics';out=d/'termination-seed20261202-20260924-audit-v1';out.mkdir(exist_ok=False)
pin=Path('/home/wangjiarui/artgym-pinned-termination-multiseed-20260924-v1');queue=g/'termination-seed20261202-20260924-evaluation-queue-v1.json'
jobs=json.loads(queue.read_text());state=dict(status='monitoring',pid=os.getpid(),started=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),audits=[]);previous=[]
def save():
 state['heartbeat']=datetime.datetime.now(datetime.timezone.utc).isoformat();tmp=out/'status.tmp';tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(out/'status.json')
save()
try:
 while True:
  completed=[]
  for j in jobs:
   p=g/'verification'/j['name']/'status.json';s=json.loads(p.read_text()) if p.exists() else {}
   if s.get('status')=='completed' and s.get('returncode')==0:completed.append(j['name'])
  if completed and completed!=previous:
   stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');target=out/f'audit-{len(completed):02d}-{stamp}.json'
   cmd=['/home/wangjiarui/artgym-runtime/bin/python','-m','scripts.audit_wuji_reset_range_cp_results','--root',str(root),'--queue',str(queue),'--output',str(target),'--allow-partial','--protocol-label','eight-H100 GPU5, batch332']
   with target.with_suffix('.log').open('w') as f:code=subprocess.run(cmd,cwd=pin,stdout=f,stderr=subprocess.STDOUT).returncode
   assert code==0,(target,code)
   a=json.loads(target.read_text());previous=completed;state['audits'].append(dict(path=str(target.relative_to(root)),completed=a['completed'],expected=a['expected']));state['last_audit']=str(target.relative_to(root))
   text=['# H100 training-termination checkpoint evaluation','',datetime.datetime.now(datetime.timezone.utc).isoformat(),'','All counts are independently rescored previously observed development states; not independent or hardware validation.','', '|Condition|Success / 300|Stable body / 300|A / B / C|Fourth / 32|','|---|---:|---:|---|---:|']
   for name,r in a['results'].items():text.append('|'+name+'|'+str(r['success'])+'|'+str(r['body'])+'|'+'/'.join(str(x['success']) for x in r['groups'][:3])+'|'+str(r['groups'][3]['success'])+'|')
   (out/'LATEST.md').write_text('\n'.join(text)+'\n')
   save()
  coordinator_path=d/'termination-seed20261202-20260924-evaluations-v1/status.json'
  coordinator=json.loads(coordinator_path.read_text()) if coordinator_path.exists() else {'status':'starting'}
  if len(completed)==len(jobs):
   state.update(status='completed',finished=datetime.datetime.now(datetime.timezone.utc).isoformat());save();break
  if coordinator['status']=='failed':
   state.update(status='evaluation_failed',error=coordinator.get('error'),finished=datetime.datetime.now(datetime.timezone.utc).isoformat());save();break
  save();time.sleep(300)
except BaseException as exc:
 state.update(status='failed',error=repr(exc),finished=datetime.datetime.now(datetime.timezone.utc).isoformat());save();raise

