"""Finite one-GPU jobs; no embedded authentication, pinned source, cumulative budget."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from scripts.record_wuji_robust_goal import R, D, record
from scripts.host_tool_environment import host_tool_environment


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def source_hash(root):
    digest=hashlib.sha256()
    for folder in ['scripts','isaacgymenvs','rl_games']:
        for p in sorted((root/folder).rglob('*')):
            if p.is_file() and p.suffix in ['.py','.yaml']:
                digest.update(str(p.relative_to(root)).encode());digest.update(p.read_bytes())
    return digest.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('name');p.add_argument('--gpu',type=int,required=True)
    p.add_argument('--seconds',type=int,required=True);p.add_argument('--local',action='store_true')
    p.add_argument('--reserved-phase',choices=['confirm','final','delivery'])
    p.add_argument('--remote-root',default='/tmp/artgym-robust-20261002')
    p.add_argument('--runtime',default='/home/wangjiarui/artgym-runtime/bin/python')
    p.add_argument('--disposable-precheck',action='store_true',help='Local bounded optimizer smoke only; never a scientific candidate')
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args(); command=a.command[1:] if a.command[:1]==['--'] else a.command
    assert a.seconds>0 and command and '/' not in a.name
    # Operator supplies an existing SSH argv in private environment. It is never
    # serialized, echoed or included in a public receipt.
    ssh=[] if a.local else json.loads(os.environ['WUJI_WIDTH_SSH_ARGV'])
    assert a.local or (ssh[0]=='ssh' and 'wangjiarui@10.13.160.5' in ssh and '33024' in ssh)
    state=json.loads((D/'STATE.json').read_text()); jobs=R/'runs/robust-knife-family-20261003/jobs'
    jobs.mkdir(parents=True,exist_ok=True)
    def host(shell):
        return subprocess.check_output(['bash','-c',shell] if a.local else ssh+[shell],text=True,
                                       stderr=subprocess.PIPE,timeout=25,env=host_tool_environment())
    with (jobs/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not a.local:
            assert state.get('remote_inventory_verified') and not state.get('remote_additional_consumption_unknown')
        else:
            disposable=False
            if a.disposable_precheck:
                assert 'scripts.train_wuji_unified_student' in command and '--width-arm' in command
                def value(flag):return command[command.index(flag)+1]
                assert value('--updates') in ['51216','51217']
                assert 'precheck' in Path(value('--output')).parts
                if value('--updates')=='51216':
                    assert value('--resume')=='runs/unified-student-20261001/SA-real-51200/step_051200.pth'
                    assert value('--fresh-optimization-seed')=='2026100215'
                else:
                    assert 'precheck' in Path(value('--resume')).parts and Path(value('--resume')).name=='step_051216.pth'
                    assert '--fresh-optimization-seed' not in command
                disposable=True
            assert disposable or 'scripts.static_wuji_geometry' in command or 'scripts.precheck_wuji_width_environment' in command or 'scripts.precheck_wuji_width_zero_change' in command or 'scripts.audit_g2_r800_bridge' in command or '--video' in command, 'Local GPU is preparation/rendering only'
        active=[json.loads(p.read_text()) for p in jobs.glob('*/identity.json') if not (p.parent/'result.json').exists()]
        assert len(active)<8 and not any(j['gpu']==a.gpu and j.get('local')==a.local for j in active)
        completed=state['historical_gpu_hours']+sum(json.loads(p.read_text())['gpu_hours'] for p in jobs.glob('*/result.json'))
        # Latest goal explicitly removes GPU-hour budgets; retain finite job timeouts and actual ledger.
        inventory=host('nvidia-smi --query-gpu=index,uuid,name,memory.used --format=csv,noheader,nounits')
        devices={int(row.split(',')[0]):row.split(',') for row in inventory.strip().splitlines()}
        assert a.gpu in devices
        device=devices[a.gpu]
        if not a.local:assert 'H200' in device[2] and int(device[3])<100
        else:
            processes=host('nvidia-smi --query-compute-apps=process_name --format=csv,noheader').strip().splitlines()
            assert all('ToDesk' in x for x in processes) and int(device[3])<5000
        if a.reserved_phase=='final':assert state.get('candidate_frozen')
        out=jobs/a.name;out.mkdir(exist_ok=False)
        identity=dict(name=a.name,gpu=a.gpu,gpu_uuid=device[1].strip(),gpu_count=1,device=device[2].strip(),
                      local=a.local,seconds=a.seconds,start_utc=utc(),local_pid=os.getpid(),command=command,
                      reserved_phase=a.reserved_phase,source_sha256=source_hash(R),registered_models=state['models'],
                      disposable_precheck=a.disposable_precheck,scientific_candidate=not a.disposable_precheck)
        (out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    started=time.monotonic();code=1;failure=None
    record('job_started',**identity,next='Inspect this finite job; no duplicate launch')
    try:
        if a.local:
            pin=Path('/tmp/artgym-robust-local-pins')/a.name;pin.mkdir(parents=True,exist_ok=False)
            for folder in ['scripts','isaacgymenvs','rl_games','assets','caches']:
                shutil.copytree(R/folder,pin/folder,ignore=shutil.ignore_patterns('__pycache__'))
            for folder in ['robust-knife-family-20261003','multigrasp-20260928/data']:
                shutil.copytree(R/'research'/folder,pin/'research'/folder)
            if 'scripts.precheck_wuji_width_zero_change' in command:
                # The original task checks actual grasp hemisphere identity.
                # No final states are loaded by this compatibility cache copy.
                target=pin/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000'
                assert target.exists()
            target=pin/'research/geometry-generalization-20261002';target.mkdir(parents=True)
            shutil.copy2(R/'research/geometry-generalization-20261002/BASELINE_PHYSICS.json',target)
            (pin/'runs').symlink_to(R/'runs',target_is_directory=True)
            assert source_hash(pin)==identity['source_sha256']
            runtime='/home/agiuser/miniconda3/envs/artgym/bin/python'
        else:
            pin=Path(a.remote_root)/'pins'/a.name
            host('mkdir -p '+shlex.quote(str(pin))+' && cp -a '+shlex.quote(a.remote_root+'/source/.')+' '+shlex.quote(str(pin))+'/ && ln -s '+shlex.quote(a.remote_root+'/runs')+' '+shlex.quote(str(pin/'runs')))
            runtime=a.runtime
            audit="from pathlib import Path;from scripts.wuji_width_jobs import source_hash;print(source_hash(Path('.')))"
            assert host('cd '+shlex.quote(str(pin))+' && python3 -c '+shlex.quote(audit)).strip()==identity['source_sha256']
        lib=str(Path(runtime).parents[1]/'lib')
        env=dict(CUDA_VISIBLE_DEVICES=str(a.gpu),LD_LIBRARY_PATH=lib,PYTHONPATH='.:rl_games',
                 TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',
                 MAX_JOBS='2',PYTHONNOUSERSITE='1',PYTHONUNBUFFERED='1',PATH=str(Path(runtime).parent)+':/usr/bin:/bin')
        if command[0]=='PYTHON':command[0]=runtime
        execution_receipt='runs/robust-knife-family-20261003/jobs/'+a.name+'/execution.json'
        bounded=['timeout','--signal=TERM','--kill-after=30',str(a.seconds),*command]
        wrapper=['python3','-m','scripts.execute_wuji_width_pin','--receipt',execution_receipt,'--',*bounded]
        shell='cd '+shlex.quote(str(pin))+' && env '+' '.join(k+'='+shlex.quote(v) for k,v in env.items())+' '+shlex.join(wrapper)
        identity.update(pin=str(pin),runtime=runtime,executed_command=command,pinned_source_verified=True)
        (out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
        with (out/'stdout.log').open('w') as log:
            code=subprocess.call(['bash','-c',shell] if a.local else ssh+[shell],stdout=log,stderr=subprocess.STDOUT,env=host_tool_environment())
    except Exception as error:
        # Exception types only: subprocess reprs can expose SSH auth arguments.
        failure=type(error).__name__
    finally:
        elapsed=time.monotonic()-started
        unknown=False
        if not a.local and identity.get('pinned_source_verified'):
            try:
                execution=json.loads(host('cat '+shlex.quote(str(Path(a.remote_root)/execution_receipt))))
                (out/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
                unknown=execution['status']!='finished'
                if not unknown:code=execution['exit_code']
            except Exception:unknown=True
        # A lost transport is not proof the remote GPU stopped. Charge a
        # conservative whole timeout until its surviving receipt is reconciled.
        charged=max(elapsed,a.seconds+30) if unknown else elapsed
        result=dict(**identity,end_utc=utc(),exit_code=code,failure_type=failure,wall_seconds=elapsed,gpu_hours=charged/3600,
                    remote_status_unknown=unknown,accounting='timeout upper bound pending remote receipt' if unknown else 'allocated wall time')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        record('job_status_unknown' if unknown else 'job_finished',**result,
               state_updates=dict(remote_additional_consumption_unknown=True) if unknown else {},
               next='Reconcile surviving remote execution receipt before further launches' if unknown else 'Check output and receipt before dependent jobs')
    raise SystemExit(code)


if __name__=='__main__':main()
