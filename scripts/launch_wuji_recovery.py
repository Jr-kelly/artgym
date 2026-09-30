"""Launch authorized host jobs from a committed immutable source snapshot.

Runs/assets/data are shared across snapshots; Python/task/config source is pinned.
"""
import argparse,json,subprocess,sys,datetime,hashlib,tarfile,io
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/artmanip-recovery-20260930'
SSH=['ssh','-i','/home/agiuser/.ssh/id_ed25519_h200','-p','33024','wangjiarui@10.13.160.5']
REMOTE='/tmp/artgym-recovery-20260930'
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--gpu',type=int,choices=[0,1],required=True);p.add_argument('--timeout',type=int,required=True);p.add_argument('--final',action='store_true',help='Frozen evaluation only; uses reserved final time/GPU budget');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    # Reject uncommitted source changes; reporting files may change during work.
    dirty=subprocess.check_output(['git','status','--porcelain','--','scripts','isaacgymenvs','rl_games'],cwd=R,text=True)
    if dirty.strip():raise RuntimeError('Commit source before launching: '+dirty)
    if a.final:
        freeze_path=D/'final-freeze.json'
        frozen=json.loads(freeze_path.read_text())
        tracked=subprocess.check_output(['git','show','HEAD:research/artmanip-recovery-20260930/final-freeze.json'],cwd=R)
        if tracked!=freeze_path.read_bytes():raise RuntimeError('Commit the exact final freeze before opening final evaluation')
        command=a.command[1:] if a.command[:1]==['--'] else a.command
        if len(command)<3 or command[1]!='-m' or command[2] not in ['scripts.evaluate_wuji_recovery_batch','scripts.evaluate_wuji_recovery']:
            raise RuntimeError('Reserved final budget is for frozen physical evaluation/video, not training')
        sha=frozen['source_sha']  # Keep final simulator/scorer code fixed across jobs.
    # Reserve outstanding wrapper time as well as elapsed usage. Refresh actual
    # process state first: a stale handoff is not a resource or budget receipt.
    subprocess.run([sys.executable,'-m','scripts.status_wuji_recovery'],cwd=R,stdout=subprocess.DEVNULL,check=True)
    state=json.loads((D/'STATE.json').read_text());now=datetime.datetime.now(datetime.timezone.utc)
    devices={(j.get('host','authorized_remote'),j['gpu']) for j in state['active_jobs']}
    if len(devices|{('authorized_remote',a.gpu)})>state['max_concurrent_gpus']:
        raise RuntimeError('Global local/remote GPU concurrency limit would be exceeded')
    if a.final and any(not j.get('final_phase',False) for j in state['active_jobs']):
        raise RuntimeError('Finish development/training jobs before opening the final cohort')
    cutoff=datetime.datetime.fromisoformat(state['deadline_utc'] if a.final else state['training_cutoff_utc'])
    if (cutoff-now).total_seconds()<a.timeout:raise RuntimeError('Job would exceed reserved final-validation cutoff')
    outstanding_seconds=sum(max(0,j['timeout_seconds']-(now-datetime.datetime.fromisoformat(j['started'])).total_seconds()) for j in state['active_jobs'])
    ceiling = state['max_gpu_hours'] if a.final else state['max_gpu_hours'] - max(2, state['reserved_final_gpu_hours'])
    if state.get('gpu_hours',0)+state.get('unmetered_cuda_preflight_reserve_gpu_hours',.05)+(outstanding_seconds+a.timeout)/3600 > ceiling:
        raise RuntimeError('Job timeout could consume reserved final GPU budget; shorten or finalize')
    spec=dict(name=a.name,gpu=a.gpu,timeout=a.timeout,final_phase=a.final,command=a.command[1:] if a.command[:1]==['--'] else a.command,source_sha=sha,created_utc=now.isoformat(),budget_receipt_utc=state['last_resource_check_utc'],occupied_gpu_hours=state['gpu_hours'],other_jobs_reserved_gpu_hours=outstanding_seconds/3600)
    archive=subprocess.check_output(['git','archive',sha,'scripts','isaacgymenvs','rl_games'],cwd=R)
    pin=REMOTE+'/pins/'+sha
    # Extract only committed code, never overwrite an existing immutable pin.
    setup="import sys,tarfile,io,os,shutil; from pathlib import Path; p=Path("+repr(pin)+"); data=sys.stdin.buffer.read(); exists=p.exists(); p.mkdir(parents=True,exist_ok=True); tarfile.open(fileobj=io.BytesIO(data)).extractall(p) if not exists else None; [(p/x).symlink_to(Path("+repr(REMOTE)+")/x,target_is_directory=True) for x in ['caches','research','runs'] if not (p/x).exists()]; shutil.copytree(Path("+repr(REMOTE)+")/'assets',p/'assets',copy_function=os.link) if not (p/'assets').exists() else None"
    subprocess.run(SSH+['python3 -c '+__import__('shlex').quote(setup)],input=archive,check=True)
    launch='''import json,subprocess,os,sys
from pathlib import Path
s=json.loads(sys.stdin.read());root=Path(s['root']);pin=Path(s['pin']);out=root/'runs/artmanip-recovery-20260930';out.mkdir(parents=True,exist_ok=True)
for f in out.glob('*/status.json'):
    old=json.loads(f.read_text())
    if old.get('status') in ['running','waiting_lease'] and old.get('gpu')==s['gpu']:
        try:os.kill(old['pid'],0)
        except ProcessLookupError:continue
        raise RuntimeError('Existing live wrapper '+str(f))
assert not (out/s['name']).exists()
env=dict(os.environ,PYTHONPATH=str(pin)+':'+str(pin/'rl_games'),LD_LIBRARY_PATH='/tmp/wuji-recovery-runtime/lib',TORCH_EXTENSIONS_DIR='/tmp/wuji-recovery-extensions',WUJI_RECOVERY_FINAL_PHASE='1' if s['final_phase'] else '0')
cmd=['/tmp/wuji-recovery-runtime/bin/python','-m','scripts.run_wuji_recovery_job','--name',s['name'],'--gpu',str(s['gpu']),'--timeout',str(s['timeout']),'--']+s['command']
with (out/(s['name']+'-launch.log')).open('w') as f:
    child=subprocess.Popen(cmd,cwd=pin,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
s['pid']=child.pid;(out/(s['name']+'-spec.json')).write_text(json.dumps(s,indent=2)+'\\n');print(json.dumps(s))
'''
    spec.update(root=REMOTE,pin=pin)
    result=json.loads(subprocess.check_output(SSH+['python3 -c '+__import__('shlex').quote(launch)],input=json.dumps(spec).encode()))
    receipts=D/'jobs';receipts.mkdir(exist_ok=True);(receipts/(a.name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    state['active_jobs'].append(result);state['phase']='B/C active; actual stages and next decisions in active_jobs and next_actions'
    (D/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    from scripts.record_wuji_recovery import record
    record('job_started',**result,next='Poll wrapper status and evidence before any further launch on this GPU')
    print(json.dumps(result))
if __name__=='__main__':main()
