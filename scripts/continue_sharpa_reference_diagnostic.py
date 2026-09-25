"""Continue the failed reference lineage after the bounded recovery passes.

Keep its physics, reward, optimizer and original 6250-epoch budget. An isolated
three-epoch preflight exercises the physics recorder before the formal branch.
Checkpoint restore cannot restore PhysX state and is not bitwise continuation.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    predecessor = root / 'runs/sharpa_paper_reference_recover1050_v1'
    name = 'sharpa_paper_reference_physics_audit1100_v1'
    run = root / 'runs' / name
    run.mkdir(exist_ok=False)
    state = dict(status='waiting_for_predecessor', started=now(), stages=[],
                 scope=__doc__, source_epoch=1100, target_epoch=6250,
                 predecessors=['sharpa_paper_reference', predecessor.name])
    status = run / 'pipeline-status.json'
    atomic_json(status, state)
    try:
        deadline = time.monotonic() + 7200
        while time.monotonic() < deadline:
            previous = json.loads((predecessor / 'pipeline-status.json').read_text())
            if previous['status'] == 'completed':
                assert all(s['returncode'] == 0 for s in previous['stages'])
                break
            if previous['status'] == 'failed':
                raise RuntimeError('Bounded recovery failed; preserve the failure and do not auto-repair')
            time.sleep(30)
        else:
            raise TimeoutError('Bounded recovery has not completed within two hours')
        (run / 'predecessor-status.json').write_text(json.dumps(previous, indent=2) + '\n')
        gate = json.loads((root / 'runs/wuji-goal/diagnostics/physics-finite-recorder-selfcheck/report.json').read_text())
        assert gate['status'] == 'verified' and gate['nonfinite_stops_without_repair']
        checkpoint = predecessor / 'checkpoints/epoch_001100.pth'
        assert json.loads(checkpoint.with_suffix('.json').read_text())['epoch'] == 1100
        state['source_checkpoint_sha256'] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        files = ['scripts/train_with_physics_finite_audit.py', 'scripts/train_with_finite_audit.py',
                 'scripts/continue_sharpa_reference_diagnostic.py', 'isaacgymenvs/tasks/artmanip.py']
        state['sources'] = {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files}
        for f in files:
            copy = run / 'entrypoint-sources' / f
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes((root / f).read_bytes())
        environment = runtime_environment(dict(project=str(root), python=sys.executable))
        environment.update(CUDA_VISIBLE_DEVICES='0,1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
        check = '''import torch,sys,json
p=torch.load(sys.argv[1],map_location='cpu')
bad=[];count=[0]
def visit(v,path):
 if torch.is_tensor(v):
  count[0]+=1
  if v.is_floating_point() and not torch.isfinite(v).all():bad.append(path)
 elif isinstance(v,dict):
  for k,x in v.items():visit(x,path+'/'+str(k))
 elif isinstance(v,(list,tuple)):
  for k,x in enumerate(v):visit(x,path+'/'+str(k))
visit(p,'checkpoint')
print(json.dumps(dict(status='finite' if not bad else 'nonfinite',tensors=count[0],bad=bad)))
assert not bad,bad
'''
        result = subprocess.run([sys.executable, '-c', check, str(checkpoint)], cwd=root,
                                env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (run / 'checkpoint-finiteness.json').write_text(result.stdout)
        (run / 'checkpoint-finiteness.stderr').write_text(result.stderr)
        result.check_returncode()
        for stage, target in [('preflight', 1103), ('teacher', 6250)]:
            experiment = name + '_smoke' if stage == 'preflight' else name
            environment.update(WUJI_FINITE_AUDIT_DIR=str(run / stage / 'finite-audit'),
                               WUJI_PHYSICS_AUDIT_DIR=str(run / stage / 'physics-audit'))
            command = [sys.executable, '-m', 'torch.distributed.run', '--standalone', '--nnodes=1',
                       '--nproc_per_node=2', '-m', 'scripts.train_with_physics_finite_audit',
                       'task=artmanip_paper_reference', 'hand=sharpa', 'object=knife_sharpa_official',
                       'train=paperReferenceSAPG', 'num_envs=10000', 'experiment=' + experiment,
                       'max_iterations=' + str(target), 'multi_gpu=True', 'headless=True',
                       'graphics_device_id=-1', 'force_render=False', 'pipeline=gpu', 'num_subscenes=0',
                       'seed=20260921', 'checkpoint=' + str(checkpoint), 'train.params.config.save_frequency=50']
            with (run / (stage + '.log')).open('w') as log:
                child = subprocess.Popen(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT)
            record = dict(name=stage, status='running', started=now(), pid=child.pid, command=command)
            state['stages'].append(record)
            state['status'] = stage
            atomic_json(status, state)
            code = child.wait()
            record.update(returncode=code, status='completed' if code == 0 else 'failed', finished=now())
            atomic_json(status, state)
            if code:
                raise RuntimeError(stage + ' failed with exit ' + str(code))
        state.update(status='completed', finished=now())
        atomic_json(status, state)
    except Exception as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        atomic_json(status, state)
        raise


if __name__ == '__main__':
    main()
