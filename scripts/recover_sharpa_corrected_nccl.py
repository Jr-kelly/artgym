"""Resume the recorded corrected-reference NCCL failure on an exclusive pair.

Wait for both four-card horizon experiments and their physics queues to finish.
Keep the original failed run; resume full model/optimizer state from CP1500 in
a new run after three real preflight epochs. PhysX state is not serialized, so
this is not bitwise continuation. No communication timeout is relaxed and no
reward, actuator, observation, optimizer or physics setting is repaired.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def gpu_processes(indices):
    gpu_rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid', '--format=csv,noheader,nounits'], text=True)
    selected = {row.split(',')[1].strip() for row in gpu_rows.splitlines() if int(row.split(',')[0]) in indices}
    rows = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid,process_name', '--format=csv,noheader,nounits'], text=True)
    return [row for row in rows.splitlines() if len(row.split(',')) >= 2 and row.split(',')[1].strip() in selected]


def main():
    root = Path(__file__).resolve().parents[1]
    original = root / 'runs/sharpa_reward_corrected'
    run = root / 'runs/sharpa_reward_corrected_recover1500_exclusive_v1'
    run.mkdir(exist_ok=False)
    state = dict(status='checking_source', started=now(), stages=[], scope=__doc__, owner='four', gpus=[0, 3])
    status_path = run / 'pipeline-status.json'
    atomic_json(status_path, state)
    try:
        previous = json.loads((original / 'pipeline-status.json').read_text())
        assert previous['status'] == 'failed' and previous['stages'][-1]['returncode'] == 1
        source_log = (original / 'teacher.log').read_text()
        assert 'NCCL watchdog' in source_log and 'Timeout(ms)=600000' in source_log
        (run / 'original-failure-status.json').write_text(json.dumps(previous, indent=2) + '\n')
        (run / 'original-failure-log-tail.txt').write_text(source_log[-24000:])
        checkpoint = original / 'checkpoints/epoch_001500.pth'
        metadata = json.loads(checkpoint.with_suffix('.json').read_text())
        assert metadata['epoch'] == 1500 and metadata['world_size'] == 2
        state['source_checkpoint_sha256'] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        state['sources'] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            Path(__file__), root / 'scripts/train_with_physics_finite_audit.py',
            root / 'scripts/train_with_finite_audit.py', root / 'isaacgymenvs/tasks/artmanip.py']}
        environment = runtime_environment(dict(project=str(root), python=sys.executable))
        environment.update(CUDA_VISIBLE_DEVICES='0,3', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
        checker = '''import torch,sys,json
payload=torch.load(sys.argv[1],map_location='cpu')
bad=[];count=[0]
def walk(v,path):
 if torch.is_tensor(v):
  count[0]+=1
  if not torch.isfinite(v).all():bad.append(path)
 elif isinstance(v,dict):
  for k,x in v.items():walk(x,path+'/'+str(k))
 elif isinstance(v,(list,tuple)):
  for k,x in enumerate(v):walk(x,path+'/'+str(k))
walk(payload,'root')
print(json.dumps(dict(tensors=count[0],bad=bad,all_finite=not bad)))
assert not bad,bad
'''
        checked = subprocess.run([sys.executable, '-c', checker, str(checkpoint)], cwd=root,
                                 env=environment, capture_output=True, text=True)
        (run / 'checkpoint-finiteness.json').write_text(checked.stdout)
        (run / 'checkpoint-finiteness.stderr').write_text(checked.stderr)
        checked.check_returncode()
        dependencies = ['wuji_horizon20_near5_cp50_seed33_v1', 'wuji_horizon60_near5_cp50_seed33_v1']
        queue_paths = [root / 'runs/wuji-goal' / ('audit-queue-' + name + '.json') for name in dependencies]
        queue_paths.append(root / 'runs/wuji-goal/audit-queue-extended60-and-functional-frame.json')
        jobs = [job['name'] for path in queue_paths for job in json.loads(path.read_text())]
        deadline = time.monotonic() + 21600
        while True:
            unfinished_runs, unfinished_jobs = [], []
            for name in dependencies:
                path = root / 'runs' / name / 'pipeline-status.json'
                current = json.loads(path.read_text())
                if current['status'] != 'completed':
                    unfinished_runs.append(dict(name=name, status=current['status']))
            for name in jobs:
                path = root / 'runs/wuji-goal/verification' / name / 'status.json'
                current = json.loads(path.read_text()) if path.exists() else {}
                if current.get('status') not in ['completed', 'failed', 'cancelled_reallocation']:
                    unfinished_jobs.append(name)
            busy = gpu_processes({0, 3})
            state.update(status='waiting_for_exclusive_gpus', heartbeat=now(),
                         unfinished_runs=unfinished_runs, unfinished_jobs=unfinished_jobs, gpu_processes=busy)
            atomic_json(status_path, state)
            if not unfinished_runs and not unfinished_jobs and not busy:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('Exclusive recovery pair did not become available within six hours; no duplicate launch')
            time.sleep(30)
        for stage, target in [('preflight', 1503), ('teacher', 6250)]:
            if gpu_processes({0, 3}):
                raise RuntimeError('The reserved pair was occupied before launch')
            experiment = run.name + '_smoke' if stage == 'preflight' else run.name
            command = list(previous['stages'][-1]['command'])
            command[0] = sys.executable
            command[command.index('isaacgymenvs.train')] = 'scripts.train_with_physics_finite_audit'
            command = [item for item in command if not item.startswith(('experiment=', 'max_iterations=', 'checkpoint='))]
            command += ['experiment=' + experiment, 'max_iterations=' + str(target),
                        'checkpoint=' + str(checkpoint), 'train.params.config.save_frequency=50']
            environment.update(WUJI_FINITE_AUDIT_DIR=str(run / stage / 'finite-audit'),
                               WUJI_PHYSICS_AUDIT_DIR=str(run / stage / 'physics-audit'))
            with (run / (stage + '.log')).open('w') as log:
                child = subprocess.Popen(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT)
            record = dict(name=stage, status='running', started=now(), pid=child.pid, command=command)
            state['stages'].append(record)
            state['status'] = stage
            atomic_json(status_path, state)
            code = child.wait()
            record.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
            atomic_json(status_path, state)
            if code:
                raise RuntimeError(stage + ' failed; see preserved logs')
        state.update(status='completed', finished=now())
        atomic_json(status_path, state)
    except Exception as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        atomic_json(status_path, state)
        raise


if __name__ == '__main__':
    main()
