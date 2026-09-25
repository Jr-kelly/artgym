"""Run declared jobs sequentially, preserving failures and GPU lease ownership."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args()
 s=json.loads(a.spec.read_text());assert os.uname().nodename==s['hostname']
 root=Path(s['root']);pin=Path(__file__).resolve().parents[1];out=root/s['output'];out.mkdir(exist_ok=False)
 state=dict(status='starting',pid=os.getpid(),started=now(),spec=s,stages=[]);child=None
 def save():state['heartbeat']=now();atomic_json(out/'status.json',state)
 try:
  for stage in s['stages']:
   command=[sys.executable,'-m',stage['module'],'--spec',str(root/stage['spec'])]
   with (out/(stage['name']+'.log')).open('w') as log:
    child=subprocess.Popen(command,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable)),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
   entry=dict(name=stage['name'],pid=child.pid,status='running',started=now(),command=command);state['stages'].append(entry);state['status']=stage['name'];save()
   while child.poll() is None:save();time.sleep(10)
   entry.update(status='completed' if child.returncode==0 else 'failed',returncode=child.returncode,finished=now());save()
   assert child.returncode==0,entry
  state.update(status='completed',finished=now())
 except BaseException as error:state.update(status='failed',error=repr(error),finished=now());raise
 finally:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=30)
  save()
if __name__=='__main__':main()
