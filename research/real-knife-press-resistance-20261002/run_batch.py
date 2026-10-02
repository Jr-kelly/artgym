"""Use the existing finite job launcher for only the registered small batch."""
import argparse,json,os,shlex,subprocess,time
from scripts.record_wuji_press_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment
p=argparse.ArgumentParser();p.add_argument('plan');a=p.parse_args();plan=json.loads((D/a.plan).read_text());ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV']);env=host_tool_environment();active={};pending=list(plan['tasks']);results=[];failed=False
record('registered_press_batch_started',evidence='research/real-knife-press-resistance-20261002/'+a.plan,next=plan['decision'])
while pending or active:
 for gpu in range(8):
  if gpu in active or not pending or failed:continue
  t=pending.pop(0);cmd=['python3','-m','scripts.wuji_press_jobs','--gpu',str(gpu),'--seconds',str(t.get('seconds',240))]
  if plan.get('reserved_phase'):cmd+=['--reserved-phase',plan['reserved_phase']]
  cmd += [t['name'],'--','PYTHON','-m','scripts.evaluate_wuji_press','--states',t['states'],'--output',t['output'],*t['args']]
  active[gpu]=(subprocess.Popen(cmd,cwd=R),t)
 for gpu,(p,t) in list(active.items()):
  code=p.poll()
  if code is not None:
   results.append(dict(name=t['name'],exit_code=code));del active[gpu]
   if code:failed=True
 if failed and not active:break
 if active:time.sleep(2)
(D/(a.plan+'.results.json')).write_text(json.dumps(results,indent=2)+'\n')
paths=[t['output'] for t in plan['tasks'] if any(r['name']==t['name'] and r['exit_code']==0 for r in results)]
if paths:subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*['wangjiarui@10.13.160.5:/tmp/artgym-press-20261002/./'+p for p in paths],str(R)+'/'],check=True,env=env,timeout=180)
record('registered_press_batch_finished',evidence='research/real-knife-press-resistance-20261002/'+a.plan+'.results.json',completed=len(paths),failed=failed,next='Inspect actual outcome then '+plan['decision'])
assert not failed
