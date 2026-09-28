"""Replace only an owned timeout supervisor; keep its actual training PID running."""
import argparse,datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(p,v):
 t=p.with_name(p.name+'.adopt-tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--old-supervisor',type=int,required=True);p.add_argument('--child',type=int,required=True);p.add_argument('--total-timeout',type=int,default=21600);a=p.parse_args()
 out=R/'runs/multigrasp-20260928'/a.name;status=out/'status.json';state=json.loads(status.read_text());assert state['status']=='running' and state['pid']==a.old_supervisor and state['child_pid']==a.child
 old=Path('/proc')/str(a.old_supervisor);child=Path('/proc')/str(a.child)
 oldcmd=(old/'cmdline').read_bytes();childcmd=(child/'cmdline').read_bytes();assert b'scripts.run_multigrasp_job' in oldcmd and a.name.encode() in oldcmd
 assert b'scripts.train_wuji_multigrasp' in childcmd and ('experiment='+a.name).encode() in childcmd
 assert int(next(x.split()[1] for x in (child/'status').read_text().splitlines() if x.startswith('PPid:')))==a.old_supervisor
 fds=[os.readlink(f) for f in (child/'fd').iterdir()];assert any('artgym-evaluation-gpu-' in x for x in fds),'Child must retain original exclusive GPU lease'
 startticks=(child/'stat').read_text().split()[21]
 receipt=dict(time=now(),old_supervisor=a.old_supervisor,unchanged_training_pid=a.child,training_start_ticks=startticks,old_command=oldcmd.decode().replace('\0',' '),training_command=childcmd.decode().replace('\0',' '),child_fd_targets=fds,old_timeout=state['timeout_seconds'],new_timeout=a.total_timeout,reason='Measured throughput projects beyond original supervisor timeout; no change to training interactions, weights, optimizer, seed or environment')
 atomic(out/'supervisor-adoption.json',receipt)
 # SIGKILL is deliberately limited to the recorded wrapper PID (not a process
 # group). It cannot execute wrapper cleanup that would terminate the child.
 os.kill(a.old_supervisor,signal.SIGKILL)
 assert child.exists() and (child/'stat').read_text().split()[21]==startticks
 state.update(pid=os.getpid(),previous_supervisor_pid=a.old_supervisor,timeout_seconds=a.total_timeout,supervisor_replaced_utc=now(),supervisor_mode='observe_existing_training_pid')
 atomic(status,state)
 with (R/'runs/multigrasp-20260928/events.jsonl').open('a') as f:f.write(json.dumps(dict(event='supervisor_adopted',**receipt))+'\n')
 started=datetime.datetime.fromisoformat(state['started']).timestamp()
 while child.exists() and (child/'stat').read_text().split()[2]!='Z':
  assert (child/'stat').read_text().split()[21]==startticks,'PID reuse'
  elapsed=time.time()-started
  if elapsed>a.total_timeout:
   os.kill(a.child,signal.SIGTERM);state['timed_out']=True;break
  state.update(heartbeat=now(),elapsed_seconds=elapsed);atomic(status,state)
  util=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True)
  with (out/'gpu.jsonl').open('a') as f:f.write(json.dumps(dict(time=now(),gpus=util))+'\n')
  time.sleep(15)
 checkpoint=R/'runs'/a.name/'checkpoints/epoch_001000.pth';log=(out/'output.log').read_text(errors='replace')
 success=not state.get('timed_out',False) and checkpoint.exists() and 'MAX EPOCHS NUM!' in log
 state.update(status='completed' if success else 'failed',finished=now(),wall_seconds=time.time()-started,returncode=None,completion_evidence='actual PID terminal + final epoch1000checkpoint + MAX EPOCHS NUM log; exit code unavailable after adoption',checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest() if checkpoint.exists() else None)
 atomic(status,state)
 with (R/'runs/multigrasp-20260928/events.jsonl').open('a') as f:f.write(json.dumps(dict(event='adopted_training_terminal',**state))+'\n')
if __name__=='__main__':main()
