"""Read-only bounded resource/process monitor for this round."""
import argparse,datetime,json,os,subprocess,time
from scripts.wuji_student_jobs import SSH,R,D
from scripts.record_wuji_student_goal import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=54000);a=p.parse_args();begin=time.monotonic();previous=None
 record('resource_monitor_started',local_pid=os.getpid(),max_seconds=a.seconds,next='Read-only GPU/PID receipts, preserveToDesk')
 while time.monotonic()-begin<a.seconds:
  now=datetime.datetime.now(datetime.timezone.utc).isoformat()
  cmd='date -u; nvidia-smi --query-gpu=index,uuid,utilization.gpu,memory.used --format=csv; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv; ps -eo pid,lstart,args'
  proc=subprocess.run(SSH+[cmd],capture_output=True,text=True,timeout=40)
  owned=[line for line in proc.stdout.splitlines() if '/tmp/wuji-student-runtime/bin/python' in line and 'bash -c' not in line]
  row=dict(utc=now,remote_exit=proc.returncode,remote=proc.stdout,local_pid=os.getpid())
  with (D/'resources.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  pids=sorted(line.split()[0] for line in owned)
  if pids!=previous:
   record('owned_remote_process_snapshot',checked_utc=now,processes=owned,evidence='research/unified-student-20261001/resources.jsonl',next='Reverify identities before any stop; noPIDassumedcurrent')
   previous=pids
  time.sleep(60)
 record('resource_monitor_finished',local_pid=os.getpid(),next='No GPU task implied by monitor status')
if __name__=='__main__':main()
