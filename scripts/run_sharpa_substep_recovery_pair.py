"""Bounded solver comparison after one-row nonfinite Sharpa physics failure.

Both branches restore the same finite CP1350, model/optimizer/counters, seed,
20000 environments and control rate. Only PhysX substeps8 versus4 differs.
Each completes a real three-epoch preflight then targets epoch1400. Original
failed runs remain intact. This is solver diagnosis, not completed replication
or bitwise resume: checkpoints do not serialize the live PhysX state.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.recover_sharpa_corrected_nccl import gpu_processes


def main():
    root=Path(__file__).resolve().parents[1]
    original=root/'runs/sharpa_paper_reference_physics_audit1100_v1'
    prior=json.loads((original/'pipeline-status.json').read_text())
    assert prior['status']=='failed' and prior['stages'][-1]['returncode']==1
    assert not (Path('/proc')/str(prior['stages'][-1]['pid'])).exists()
    event=json.loads((original/'teacher/physics-audit/rank0/nonfinite-physics.json').read_text())
    assert event['event']=='nonfinite-physics' and event['policy_update_step']==1387
    check=json.loads((root/'runs/wuji-goal/diagnostics/sharpa-paper-1387-physics-failure/analysis.json').read_text())['checkpoint']
    assert check['tensor_count']==378 and check['nonfinite']==[]
    cp=root/check['path']
    assert hashlib.sha256(cp.read_bytes()).hexdigest()==check['sha256']
    environment=runtime_environment(dict(project=str(root),python=sys.executable))
    environment.update(CUDA_VISIBLE_DEVICES='0,1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    summary_path=root/'runs/wuji-goal/diagnostics/sharpa-substep-recovery-pair.json'
    assert not summary_path.exists()
    pair=dict(status='starting',started=now(),scope=__doc__,source_checkpoint=check,runs=[])
    atomic_json(summary_path,pair)
    for substeps in [8,4]:
        name='sharpa_paper_reference_substeps%d_recover1350_v1'%substeps
        run=root/'runs'/name;run.mkdir(exist_ok=False)
        state=dict(status='preflight',started=now(),scope=__doc__,owner='eight',gpus=[0,1],
            source_checkpoint_sha256=check['sha256'],source_epoch=1350,target_epoch=1400,substeps=substeps,
            original_failure=event,stages=[],sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),root/'scripts/train_with_physics_finite_audit.py',root/'isaacgymenvs/tasks/artmanip.py']})
        (run/'original-failure-status.json').write_text(json.dumps(prior,indent=2)+'\n')
        atomic_json(run/'pipeline-status.json',state)
        pair['runs'].append(name);pair['status']='running_'+str(substeps);atomic_json(summary_path,pair)
        failed=False
        for stage,target in [('preflight',1353),('teacher',1400)]:
            busy=gpu_processes({0,1})
            if busy:raise RuntimeError('Reserved GPUs occupied before solver trial: '+repr(busy))
            command=[str(x) for x in prior['stages'][-1]['command']
                     if not str(x).startswith(('experiment=','max_iterations=','checkpoint=','train.params.config.save_frequency=','task.sim.substeps='))]
            command[0]=sys.executable
            experiment=name+'_smoke' if stage=='preflight' else name
            command+=['experiment='+experiment,'max_iterations='+str(target),'checkpoint='+str(cp),
                      'task.sim.substeps='+str(substeps),'train.params.config.save_frequency=25']
            environment.update(WUJI_FINITE_AUDIT_DIR=str(run/stage/'finite-audit'),
                               WUJI_PHYSICS_AUDIT_DIR=str(run/stage/'physics-audit'))
            with (run/(stage+'.log')).open('w') as log:
                child=subprocess.Popen(command,cwd=root,env=environment,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            item=dict(name=stage,status='running',pid=child.pid,command=command,started=now())
            state['stages'].append(item);state['status']=stage;atomic_json(run/'pipeline-status.json',state)
            code=child.wait();item.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(run/'pipeline-status.json',state)
            if code:
                failed=True;break
            metadata=json.loads((root/'runs'/experiment/'checkpoints/latest.json').read_text())
            assert metadata['epoch']==target and metadata['world_size']==2
        state.update(status='failed' if failed else 'completed',finished=now());atomic_json(run/'pipeline-status.json',state)
    pair.update(status='completed',finished=now());atomic_json(summary_path,pair)


if __name__=='__main__':main()
