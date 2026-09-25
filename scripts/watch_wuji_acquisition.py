"""External one-minute heartbeat and coordinator recovery for the four-H100 goal."""
import json,os,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runs/wuji-goal/four-gpu-watch'

if __name__=='__main__':
    STATE.mkdir(parents=True,exist_ok=True)
    command=['ssh','-p','30296','-i','/home/agiuser/.ssh/id_ed25519_h200',
        '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10',
        'wangjiarui@10.14.0.73',
        'cd /home/wangjiarui/artgym-experiments-20260921 && '
        '/home/wangjiarui/artgym-runtime/bin/python -m scripts.run_wuji_acquisition_suite --ensure']
    while True:
        try:
            response=subprocess.run(command,capture_output=True,text=True,timeout=45,check=True,
                env={k:v for k,v in os.environ.items() if k!='LD_LIBRARY_PATH'})
            status=json.loads(response.stdout)
        except Exception as error:status={'error':repr(error)}
        status['local_checked_unix']=time.time()
        temporary=STATE/'latest.tmp';temporary.write_text(json.dumps(status,indent=2));temporary.replace(STATE/'latest.json')
        print(json.dumps({k:status.get(k) for k in ['local_checked_unix','error','pid','experiments']}),flush=True)
        time.sleep(60)
