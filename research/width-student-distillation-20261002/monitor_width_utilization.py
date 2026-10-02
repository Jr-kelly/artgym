"""Finite read-only utilization sampling; authentication only in private environment."""
import csv,datetime,json,os,signal,subprocess,time
from pathlib import Path
from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_width_goal import D
ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV'])
assert '17314' in ssh and 'wangjiarui@10.13.160.5' in ssh
stop=False
def finish(*_):
 global stop
 stop=True
signal.signal(signal.SIGTERM,finish)
started=time.monotonic()
while not stop and time.monotonic()-started<14400:
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  result=subprocess.run(ssh+['nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader,nounits'],capture_output=True,text=True,timeout=25,env=host_tool_environment())
  if result.returncode:
   row=dict(utc=now,verified=False,exit_code=result.returncode)
  else:
   devices=[dict(index=int(x[0]),utilization_gpu=float(x[1]),memory_mib=int(x[2])) for x in csv.reader(result.stdout.splitlines())]
   assert len(devices)==8
   row=dict(utc=now,verified=True,devices=devices,whole_machine_utilization_pct=sum(x['utilization_gpu'] for x in devices)/8)
 except (subprocess.TimeoutExpired,ValueError,AssertionError):
  row=dict(utc=now,verified=False,error='Read-only sampling unavailable')
 with (D/'UTILIZATION_SAMPLES.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 if not stop:time.sleep(30)
