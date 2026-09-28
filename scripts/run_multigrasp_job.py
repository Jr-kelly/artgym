"""Bounded single-GPU job with lease, immutable command and resource receipts."""
import argparse,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
R=Path(__file__).resolve().parents[1]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--gpu',type=int,required=True);p.add_argument('--timeout',type=int,default=7200);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
 out=R/'runs/multigrasp-20260928'/a.name;out.mkdir(parents=True,exist_ok=False)
 cmd=a.command;cmd=cmd[1:] if cmd and cmd[0]=='--' else cmd
 cmd=[sys.executable if x=='PYTHON' else x for x in cmd]
 state=dict(name=a.name,gpu=a.gpu,command=cmd,timeout_seconds=a.timeout,started=now(),pid=os.getpid(),status='waiting_lease')
 def save():
  (out/'status.json').write_text(json.dumps(state,indent=2)+'\n')
  with (R/'runs/multigrasp-20260928/events.jsonl').open('a') as f:f.write(json.dumps(state)+'\n')
 save();lease=None;start=time.monotonic()
 while lease is None:
  lease=acquire_evaluation_gpu(a.gpu)
  if time.monotonic()-start>300:raise RuntimeError('GPU lease unavailable for 300s')
  if lease is None:time.sleep(5)
 env=runtime_environment(dict(project=str(R),python=sys.executable),a.gpu)
 with (out/'output.log').open('w') as log:
  child=subprocess.Popen(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
  state.update(status='running',child_pid=child.pid);save();last=0
  try:
   while child.poll() is None:
    t=time.monotonic()
    if t-start>a.timeout:child.terminate();child.wait(timeout=30);state['timed_out']=True;break
    if t-last>=30:
     util=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True)
     with (out/'gpu.jsonl').open('a') as f:f.write(json.dumps(dict(time=now(),gpus=util))+'\n')
     state.update(heartbeat=now(),elapsed_seconds=t-start);(out/'status.json').write_text(json.dumps(state,indent=2)+'\n');last=t
    time.sleep(3)
  finally:
   if child.poll() is None:child.terminate();child.wait(timeout=30)
 state.update(status='completed' if child.returncode==0 else 'failed',returncode=child.returncode,finished=now(),wall_seconds=time.monotonic()-start);save();lease.close()
 if child.returncode:sys.exit(child.returncode)
if __name__=='__main__':main()
