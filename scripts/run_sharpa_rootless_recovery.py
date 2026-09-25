"""After the substep pair, test empty-root removal from the same finite CP1350.

Keep4substeps,seed,20000envs,model/optimizer/counters and reference rewards.
Only replace35URDFs by versions removing an empty identity-fixed base. All
shape/joint/grasp data remain unchanged. This is not exact paper replication.
PhysX state is not serialized, so no branch is a bitwise continuation.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.recover_sharpa_corrected_nccl import gpu_processes


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    path=base/'diagnostics/sharpa-rootless-recovery-launch.json';assert not path.exists()
    state=dict(status='waiting_for_substep4',started=now(),scope=__doc__,owner='eight',gpus=[0,1]);atomic_json(path,state)
    predecessor=root/'runs/sharpa_paper_reference_substeps4_recover1350_v1/pipeline-status.json'
    deadline=time.monotonic()+10800
    while time.monotonic()<deadline:
        previous=json.loads(predecessor.read_text())
        if previous['status'] in ['completed','failed'] and not gpu_processes({0,1}):break
        time.sleep(20)
    else:raise TimeoutError('Reserved GPU pair did not finish the preceding trial')
    dataset=json.loads((base/'sharpa-rootless-dataset-manifest.json').read_text())
    assert dataset['geometries']==35 and dataset['cache_arrays_and_metadata_unchanged']
    for p,h in dataset['artifact_sha256'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h
    runtime=base/'diagnostics/sharpa-1382-rootless-state-reconstruction'
    checked=json.loads((runtime/'report.json').read_text());finished=json.loads((runtime/'status.json').read_text())
    assert finished['status']=='completed' and finished['returncode']==0
    assert checked['simulated_ticks']==120 and checked['first_nonfinite_sim_tick'] is None
    assert checked['object_profile']=='knife_sharpa_rootless_20260922'
    assert all(p['body_names']==['link_0','link_1'] for p in checked['properties'])
    cp=root/'runs/sharpa_paper_reference_physics_audit1100_v1/checkpoints/epoch_001350.pth'
    digest='91bf5c0771040522c46aa5a5d595b1c3e06c9479abb65a72b1ea4dd0b2911428'
    assert hashlib.sha256(cp.read_bytes()).hexdigest()==digest
    name='sharpa_paper_reference_rootless_recover1350_v1';run=root/'runs'/name;run.mkdir(exist_ok=False)
    env=runtime_environment(dict(project=str(root),python=sys.executable))
    env.update(CUDA_VISIBLE_DEVICES='0,1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
    original=json.loads((root/'runs/sharpa_paper_reference_physics_audit1100_v1/pipeline-status.json').read_text())['stages'][-1]['command']
    pipeline=dict(status='preflight',started=now(),scope=__doc__,gpus=[0,1],owner='eight',stages=[],source_checkpoint_sha256=digest,
        source_epoch=1350,target_epoch=1400,dataset_manifest='runs/wuji-goal/sharpa-rootless-dataset-manifest.json',
        predecessor_status=previous['status'],code_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),root/'scripts/train_with_physics_finite_audit.py',root/'isaacgymenvs/tasks/artmanip.py']})
    atomic_json(run/'pipeline-status.json',pipeline)
    state.update(status='preflight_then_training',run=name);atomic_json(path,state)
    for stage,target in [('preflight',1353),('teacher',1400)]:
        assert not gpu_processes({0,1})
        command=[str(v) for v in original if not str(v).startswith(('experiment=','max_iterations=','checkpoint=','object=','task.sim.substeps=','train.params.config.save_frequency='))]
        command[0]=sys.executable;experiment=name+'_smoke' if stage=='preflight' else name
        command+=['experiment='+experiment,'max_iterations='+str(target),'checkpoint='+str(cp),'object=knife_sharpa_rootless_20260922',
            'task.sim.substeps=4','train.params.config.save_frequency=25']
        env.update(WUJI_FINITE_AUDIT_DIR=str(run/stage/'finite-audit'),WUJI_PHYSICS_AUDIT_DIR=str(run/stage/'physics-audit'))
        with (run/(stage+'.log')).open('w') as f:
            child=subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        item=dict(name=stage,status='running',pid=child.pid,command=command,started=now());pipeline['stages'].append(item)
        pipeline['status']=stage;atomic_json(run/'pipeline-status.json',pipeline)
        code=child.wait();item.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(run/'pipeline-status.json',pipeline)
        if code:
            pipeline.update(status='failed',finished=now());atomic_json(run/'pipeline-status.json',pipeline)
            state.update(status='failed',finished=now());atomic_json(path,state);raise SystemExit(code)
        metadata=json.loads((root/'runs'/experiment/'checkpoints/latest.json').read_text())
        assert metadata['epoch']==target and metadata['world_size']==2
    pipeline.update(status='completed',finished=now());atomic_json(run/'pipeline-status.json',pipeline)
    state.update(status='completed',finished=now());atomic_json(path,state)


if __name__=='__main__':main()
