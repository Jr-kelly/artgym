"""Finite, explicit queue on one GPU; any fault returns for evidence review."""
import argparse,json,subprocess,sys
from pathlib import Path
from scripts.record_wuji_geometry_goal import record
def main():
 p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('--gpu',type=int,required=True);a=p.parse_args();jobs=json.loads(a.plan.read_text())
 record('finite_queue_started',plan=str(a.plan),gpu=a.gpu,jobs=len(jobs),local_pid=__import__('os').getpid(),next='Collect per-job receipts; no automatic restart on failure')
 for j in jobs:
  command=[sys.executable,'-m','scripts.wuji_geometry_jobs','--gpu',str(a.gpu),'--seconds',str(j['seconds'])]
  if j.get('final'):command+=['--final']
  command += [j['name'],'--','/tmp/wuji-student-runtime/bin/python','-m',j['module']]+j['args']
  code=subprocess.call(command)
  if code:
   record('finite_queue_stopped_on_failure',job=j['name'],exit_code=code,plan=str(a.plan),next='Inspect failure and preserve logs; no blind retry');raise SystemExit(code)
 record('finite_queue_completed',plan=str(a.plan),gpu=a.gpu,jobs=len(jobs),next='Inspect and analyze results before dependent work')
if __name__=='__main__':main()
