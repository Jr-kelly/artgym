"""Inspect real remote PIDs, throughput and useful-GPU sampling without restarting jobs."""
import datetime,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 rows={}
 for arm in 'ABCD':
  name='mg_'+arm+'_seed2801';out=R/'runs/multigrasp-20260928'/name;s=json.loads((out/'status.json').read_text());pid=s['child_pid'];proc=Path('/proc')/str(pid)
  cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode() if proc.exists() else None
  log=(out/'output.log').read_text(errors='replace');epochs=re.findall(r'epoch\s+:\s+([\d,]+) / ([\d,]+)',log);epoch=int(epochs[-1][0].replace(',','')) if epochs else 0
  times=[float(x) for x in re.findall(r'Time to train epoch\s+:\s+([\d.]+) s',log)][-20:]
  mean=sum(times)/len(times) if times else None
  rows[arm]=dict(status=s['status'],pid=pid,pid_exists=proc.exists(),cmdline=cmd,epoch=epoch,total_epochs=1000,mean_last20_epoch_seconds=mean,remaining_seconds_estimate=(1000-epoch)*mean if mean else None,job_elapsed_seconds=s.get('elapsed_seconds'),job_timeout_seconds=s['timeout_seconds'])
  if s['status']=='running' and not (cmd and name in cmd):raise RuntimeError('Running state does not match actual PID: '+name)
 report=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),arms=rows,gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
