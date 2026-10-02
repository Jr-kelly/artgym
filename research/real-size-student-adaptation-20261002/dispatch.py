import argparse,json,os,shlex,subprocess,time
from scripts.record_wuji_real_size_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment
p=argparse.ArgumentParser();p.add_argument('plan');a=p.parse_args();plan=json.loads((D/a.plan).read_text());ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV']);env=host_tool_environment();active={};pending=list(plan['tasks']);results=[];failed=False
record('batch_started',plan=a.plan,next=plan['decision'])
while pending or active:
 for gpu in plan.get('gpus',range(4)):
  if gpu in active or not pending or failed:continue
  t=pending.pop(0);cmd=['python3','-m','scripts.wuji_real_size_jobs','--gpu',str(gpu),'--seconds',str(t.get('seconds',240))]
  if plan.get('reserved_phase'):cmd+=['--reserved-phase',plan['reserved_phase']]
  cmd += [t['name'],'--','PYTHON','-m',*t['command']];active[gpu]=(subprocess.Popen(cmd,cwd=R),t)
 for gpu,(p,t) in list(active.items()):
  code=p.poll()
  if code is not None:
   results.append(dict(name=t['name'],exit_code=code));del active[gpu]
   if code:failed=True
 if failed and not active:break
 if active:time.sleep(2)
(D/(a.plan+'.results.json')).write_text(json.dumps(results,indent=2)+'\n')
paths=[t['output'] for t in plan['tasks'] if any(r['name']==t['name'] for r in results)]
if paths:subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*['wangjiarui@10.13.160.5:/tmp/artgym-real-size-20261002/./'+p for p in paths],str(R)+'/'],check=True,env=env,timeout=180)
record('batch_finished',plan=a.plan,results=results,next=plan['decision']);assert not failed
