"""Local one-minute watchdog for this specifically authorized eight-GPU host."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runs/eight-gpu-watch'
REMOTE='/home/wangjiarui/artgym-experiments-20260921'

if __name__=='__main__':
    STATE.mkdir(parents=True,exist_ok=True)
    command=['ssh','-p','30147','-i','/home/agiuser/.ssh/id_ed25519_h200',
        '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10',
        'wangjiarui@10.14.0.106',
        f'cd {REMOTE} && /home/wangjiarui/artgym-runtime/bin/python -m scripts.run_eight_gpu_suite --ensure']
    while True:
        env={k:v for k,v in os.environ.items() if k!='LD_LIBRARY_PATH'}
        try:
            response=subprocess.run(command,capture_output=True,text=True,timeout=45,env=env,check=True)
            status=json.loads(response.stdout)
            status['local_checked_unix']=time.time()
        except Exception as error:
            status=dict(local_checked_unix=time.time(),error=repr(error))
        target=STATE/'latest.json';temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps(status,indent=2));temporary.replace(target)
        utilization=status.get('utilization',{})
        print(json.dumps({'checked':status['local_checked_unix'],'error':status.get('error'),'remote_pid':status.get('pid'),
            'gpu_mean_5m':utilization.get('windows',{}).get('300',{}).get('mean_percent'),
            'gpu_mean_4h':utilization.get('windows',{}).get('14400',{}).get('mean_percent'),
            'utilization_alert':utilization.get('alert'),'suite_errors':status.get('errors',[])}),flush=True)
        time.sleep(60)
