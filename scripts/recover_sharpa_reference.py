"""Bounded CP1050 recovery with original paper settings and numerical guards."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    original = root / 'runs/sharpa_paper_reference'
    failure = json.loads((original / 'pipeline-status.json').read_text())
    assert failure['status'] == 'failed'
    for stage in failure['stages']:
        if stage['name'] == 'teacher':
            assert stage['returncode'] != 0
            assert not (Path('/proc') / str(stage['pid'])).exists()
    identity = root / 'runs/wuji-goal/diagnostics/sharpa-paper-reference-crash1050/checkpoint-finiteness.json'
    verified = json.loads(identity.read_text())
    assert verified['status'] == 'finite'
    checkpoint = root / verified['checkpoint']
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == verified['sha256']
    name = 'sharpa_paper_reference_recover1050_v1'
    run = root / 'runs' / name
    run.mkdir(exist_ok=False)
    (run / 'original-failure-status.json').write_bytes((original / 'pipeline-status.json').read_bytes())
    environment = runtime_environment(dict(project=str(root), python=sys.executable))
    environment.update(CUDA_VISIBLE_DEVICES='0,1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4',
                       WUJI_FINITE_AUDIT_DIR=str(run / 'finite-audit'))
    command = [sys.executable, '-m', 'torch.distributed.run', '--standalone', '--nnodes=1',
               '--nproc_per_node=2', '-m', 'scripts.train_with_finite_audit',
               'task=artmanip_paper_reference', 'hand=sharpa', 'object=knife_sharpa_official',
               'train=paperReferenceSAPG', 'num_envs=10000', 'experiment=' + name,
               'max_iterations=1100', 'multi_gpu=True', 'headless=True', 'graphics_device_id=-1',
               'force_render=False', 'pipeline=gpu', 'num_subscenes=0', 'seed=20260921',
               'checkpoint=' + str(checkpoint), 'train.params.config.save_frequency=25']
    state = dict(status='teacher', started=now(), original_failure='normal expects all elements of std >= 0.0 after epoch1062',
                 source_checkpoint_sha256=verified['sha256'], source_epoch=1050, target_epoch=1100,
                 scope='Bounded diagnostic recovery with original physics/reward/optimizer and two10000-envranks. No numerical repair. PhysX state was not serialized, so this is not bitwise continuation. Original failed run remains unchanged.',
                 code_sha256={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in
                              ['scripts/recover_sharpa_reference.py', 'scripts/train_with_finite_audit.py',
                               'isaacgymenvs/tasks/artmanip.py', 'rl_games/rl_games/common/a2c_common.py']}, stages=[])
    with (run / 'teacher.log').open('w') as log:
        process = subprocess.Popen(command, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT)
    stage = dict(name='teacher', status='running', pid=process.pid, started=now(), command=command)
    state['stages'].append(stage)
    atomic_json(run / 'pipeline-status.json', state)
    code = process.wait()
    stage.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
    state.update(status=stage['status'], finished=now())
    atomic_json(run / 'pipeline-status.json', state)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
