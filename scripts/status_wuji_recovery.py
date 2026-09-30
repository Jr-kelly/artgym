"""Refresh current process evidence and conservative occupied-GPU wall accounting."""
import json,subprocess,datetime,argparse,shlex,fcntl
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
    for job in result['jobs']:job['host']='authorized_remote'
    # Only explicitly registered jobs belong to this goal. Remote rsync does
    # not delete these uniquely named local outputs.
    local_jobs=[]
    for registration in sorted((D/'local-jobs').glob('*.json')):
        spec=json.loads(registration.read_text());assert spec['name'].startswith('local-')
        path=R/spec['status_path'];job=json.loads(path.read_text()) if path.exists() else dict(spec,status='waiting_lease',started=spec['created_utc'],timeout_seconds=spec['timeout'])
        assert job['name']==spec['name'] and job['gpu']==spec['gpu'] and job['pid']==spec['pid']
        job.update(host='local',path=str(path),final_phase=True)
        try:
            args=Path(f"/proc/{job['pid']}/cmdline").read_bytes().split(b'\0')
            job['pid_exists']=b'scripts.run_wuji_recovery_job' in args and job['name'].encode() in args
        except (FileNotFoundError,ProcessLookupError):job['pid_exists']=False
        if not job['pid_exists'] and job['status'] in ['waiting_lease','running']:
            job.update(status='failed',finished=result['utc'],failure='Registered local wrapper absent at resource check')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(job,indent=2)+'\n')
        local_jobs.append(job)
    result['jobs']+=local_jobs
    if local_jobs:result['local_gpus']=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,utilization.gpu,memory.used','--format=csv,noheader'],text=True)
    receipt=D/'resources';receipt.mkdir(exist_ok=True);(receipt/'latest.json').write_text(json.dumps(result,indent=2)+'\n')
    with (D/'.event.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        state=json.loads((D/'STATE.json').read_text());finished=state.setdefault('recorded_finished_jobs',[])
        now=datetime.datetime.fromisoformat(result['utc']);gpu_hours=0;hours_by_host={'authorized_remote':0.,'local':0.}
        for job in result['jobs']:
            start=datetime.datetime.fromisoformat(job['started']);end=datetime.datetime.fromisoformat(job['finished']) if 'finished' in job else now
            duration=(end-start).total_seconds()/3600;gpu_hours+=duration;hours_by_host[job['host']]+=duration
        state['gpu_hours']=gpu_hours;state['unmetered_cuda_preflight_reserve_gpu_hours']=.05;state['active_jobs']=[j for j in result['jobs'] if j['status'] in ['running','waiting_lease'] and j['pid_exists']];state['last_resource_check_utc']=result['utc']
        state['gpu_hours_by_host']=hours_by_host
        assert len({(j['host'],j['gpu']) for j in state['active_jobs']})<=state['max_concurrent_gpus']
        newly=[j for j in result['jobs'] if j['status'] in ['completed','failed'] and j['name'] not in finished]
        state['recorded_finished_jobs']+= [j['name'] for j in newly]
        (D/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    if a.pull:
        subprocess.run(['rsync','-a','--exclude=*.pth','--exclude=*.npz','--exclude=*.mp4','-e','ssh -i /home/agiuser/.ssh/id_ed25519_h200 -p 33024','wangjiarui@10.13.160.5:'+REMOTE+'/runs/artmanip-recovery-20260930/',str(R/'runs/artmanip-recovery-20260930/')],check=True)
    for j in newly:record('job_finished',job=j,gpu_hours=gpu_hours,next='Read evidence and decide follow-up; process state verified at '+result['utc'])
    print(json.dumps(dict(utc=result['utc'],gpu_hours=gpu_hours,gpus=result['gpus'],active=[dict(name=j['name'],pid=j['pid'],gpu=j['gpu']) for j in state['active_jobs']],newly_finished=[dict(name=j['name'],status=j['status']) for j in newly],learning={name:[{k:r[k] for k in ['epoch','frame_after','optimizer_updates','wall_seconds','lr','reward_weights','source_visits']} for r in rows] for name,rows in result['learning'].items()})))
if __name__=='__main__':main()
