"""Bounded local evidence mirror; does not start or stop simulation jobs."""
import argparse,datetime,json,shlex,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R.parent
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-i','/home/agiuser/.ssh/id_ed25519_h200','-o','IdentitiesOnly=yes','-p','30296','wangjiarui@10.14.0.93']
REMOTE='/home/wangjiarui/artgym-multigrasp-20260928'
def main():
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=42000);a=p.parse_args();start=time.monotonic();seen={}
 out=R/'research/multigrasp-20260928/receipts';out.mkdir(parents=True,exist_ok=True)
 while time.monotonic()-start<a.seconds:
  now=datetime.datetime.now(datetime.timezone.utc).isoformat()
  code="import json,pathlib,subprocess; r=pathlib.Path("+repr(REMOTE)+"); print(json.dumps({'jobs':{p.parent.name:json.loads(p.read_text()) for p in (r/'runs/multigrasp-20260928').glob('*/status.json')},'initial_models':{p.parent.name:json.loads(p.read_text()) for p in (r/'runs').glob('*/initial-model.json')},'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True)}))"
  try:
   result=subprocess.run(SSH+['/home/wangjiarui/artgym-runtime/bin/python -c '+shlex.quote(code)],text=True,capture_output=True,timeout=30,check=True);v=json.loads(result.stdout);v['observed_utc']=now
   (out/'monitor-latest.json').write_text(json.dumps(v,indent=2)+'\n')
   with (out/'gpu-history.jsonl').open('a') as f:f.write(json.dumps(dict(time=now,gpu=v['gpu']))+'\n')
   for name,state in v['jobs'].items():
    status=state['status']
    if seen.get(name)==status:continue
    seen[name]=status;e=dict(event='observed_remote_transition',time=now,name=name,remote=REMOTE,host='.93:30296',state=state,evidence='research/multigrasp-20260928/receipts/monitor-latest.json',next='review complete evidence; preserve failed runs')
    for p in [R/'runs/multigrasp-20260928/events.jsonl',B/'runs/wuji-goal/journal/events.jsonl']:
     with p.open('a') as f:f.write(json.dumps(e)+'\n')
    for p in [R/'WUJI_MULTIGRASP_HANDOFF.md',B/'WUJI_GOAL_HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
     with p.open('a') as f:f.write('\n多抓姿实查 '+now+' '+name+' '+status+'；远端PID '+str(state.get('child_pid'))+'；证据 '+e['evidence']+'，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。\n')
    if status in ['completed','failed']:
     subprocess.run(['rsync','-a','--exclude=*.pth','-e',shlex.join(SSH[:-1]),SSH[-1]+':'+REMOTE+'/runs/multigrasp-20260928/'+name+'/',str(R/'runs/multigrasp-20260928'/name)+'/'],check=True,timeout=50)
  except Exception as exc:
   with (out/'monitor-errors.jsonl').open('a') as f:f.write(json.dumps(dict(time=now,error=repr(exc)))+'\n')
  time.sleep(30)
if __name__=='__main__':main()
