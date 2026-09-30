"""Refresh current process evidence and conservative occupied-GPU wall accounting."""
import json,subprocess,datetime,argparse,shlex
from pathlib import Path
from scripts.launch_wuji_recovery import SSH,REMOTE,R,D
from scripts.record_wuji_recovery import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--pull',action='store_true');a=p.parse_args()
    code='''import json,os,subprocess,datetime
from pathlib import Path
root=Path('/tmp/artgym-recovery-20260930');jobs=[];learning={}
for p in (root/'runs/artmanip-recovery-20260930').glob('*/status.json'):
 s=json.loads(p.read_text());s['path']=str(p)
 try:os.kill(s['pid'],0);s['pid_exists']=True
 except ProcessLookupError:s['pid_exists']=False
 jobs.append(s)
for p in (root/'runs').glob('recovery-*/learning.jsonl'):
 lines=p.read_text().splitlines();learning[p.parent.name]=[json.loads(x) for x in lines[-2:]]
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),jobs=jobs,learning=learning,gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True))))
'''
    result=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)]))
    receipt=D/'resources';receipt.mkdir(exist_ok=True);(receipt/'latest.json').write_text(json.dumps(result,indent=2)+'\n')
    state=json.loads((D/'STATE.json').read_text());finished=state.setdefault('recorded_finished_jobs',[])
    now=datetime.datetime.fromisoformat(result['utc']);gpu_hours=0
    for job in result['jobs']:
        start=datetime.datetime.fromisoformat(job['started']);end=datetime.datetime.fromisoformat(job['finished']) if 'finished' in job else now
        gpu_hours+=(end-start).total_seconds()/3600
    state['gpu_hours']=gpu_hours;state['unmetered_cuda_preflight_reserve_gpu_hours']=.05;state['active_jobs']=[j for j in result['jobs'] if j['status'] in ['running','waiting_lease'] and j['pid_exists']];state['last_resource_check_utc']=result['utc']
    newly=[j for j in result['jobs'] if j['status'] in ['completed','failed'] and j['name'] not in finished]
    state['recorded_finished_jobs']+= [j['name'] for j in newly]
    (D/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    if a.pull:
        subprocess.run(['rsync','-a','--exclude=*.pth','--exclude=*.npz','--exclude=*.mp4','-e','ssh -i /home/agiuser/.ssh/id_ed25519_h200 -p 33024','wangjiarui@10.13.160.5:'+REMOTE+'/runs/artmanip-recovery-20260930/',str(R/'runs/artmanip-recovery-20260930/')],check=True)
    for j in newly:record('job_finished',job=j,gpu_hours=gpu_hours,next='Read evidence and decide follow-up; process state verified at '+result['utc'])
    print(json.dumps(dict(utc=result['utc'],gpu_hours=gpu_hours,gpus=result['gpus'],active=[dict(name=j['name'],pid=j['pid'],gpu=j['gpu']) for j in state['active_jobs']],newly_finished=[dict(name=j['name'],status=j['status']) for j in newly],learning=result['learning'])))
if __name__=='__main__':main()
