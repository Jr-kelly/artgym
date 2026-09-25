"""Small, isolated SAPG acquisition experiment with automatic checkpoint evaluation.

Does not stop or modify the paper-baseline runs. Evaluation uses the one training
grasp, so its results must not be reported as held-out/generalization performance.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from rl_games.common.checkpoint_schedule import atomic_json

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def evaluate(run, record, environment):
    output = run / 'evaluation' / f"epoch_{record['epoch']:06d}"
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'isaacgymenvs.eval_consecutive',
               '--checkpoint', record['policy_checkpoint'], '--summary-output', str(output / 'summary.json'),
               '--task', 'wuji_demo_aligned', '--hand', 'wuji_paper',
               '--object', 'knife_wuji_demo_aligned', '--train', 'wujiDemoAlignedSAPG',
               '--instance-id', '000', '--grasp-split', 'train', '--episodes-per-grasp', '5',
               '--max-steps', '1440', '--headless', '--graphics-device-id', '-1',
               '--deterministic', '--randomize', 'False', '--seed', '20260921']
    result = dict(record, status='running', started=now(), command=command,
                  evaluation_scope='One training grasp, deterministic, no randomization; acquisition only')
    atomic_json(run / 'evaluation/status.json', result)
    try:
        with (output / 'evaluation.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, env=environment, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=600)
        result.update(json.loads((output / 'summary.json').read_text()), status='completed')
        best_path = run / 'evaluation/best.json'
        best = json.loads(best_path.read_text()) if best_path.exists() else None
        score = lambda r: (r['execution_success_rate'], r['mean_cycles'])
        if best is None or score(result) > score(best):
            atomic_json(best_path, result)
            link = run / 'evaluation/.best.tmp'
            link.unlink(missing_ok=True)
            link.symlink_to(os.path.relpath(record['policy_checkpoint'], link.parent))
            link.replace(run / 'evaluation/best.pth')
        atomic_json(run / 'evaluation/latest.json', result)
    except Exception as error:
        result.update(status='failed', error=repr(error))
    result['finished'] = now()
    atomic_json(output / 'result.json', result)
    atomic_json(run / 'evaluation/status.json', result)
    with (run / 'evaluation/history.jsonl').open('a') as stream:
        stream.write(json.dumps(result) + '\n')
    print('evaluation', record['epoch'], result['status'], result.get('execution_success_rate'), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--envs', type=int, default=640)
    parser.add_argument('--epochs', type=int, default=1000)
    parser.add_argument('--gpu', type=int, default=2)
    parser.add_argument('--preflight-report', type=Path, required=True)
    args = parser.parse_args()
    if args.envs <= 0 or args.envs % 5 or args.epochs <= 0:
        raise ValueError('Positive environment count must be divisible by five SAPG groups')
    report = json.loads(args.preflight_report.read_text())
    if (report['controller'] != 'replay' or report['pipeline'] != 'gpu'
            or report['passed_environments'] != report['num_envs']):
        raise ValueError('Require a passing GPU reference replay before training')
    run = args.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=True)
    if (run / 'pipeline-status.json').exists():
        raise ValueError('Use a fresh run directory')
    lock = (run / 'pipeline.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    environment = dict(os.environ, CUDA_VISIBLE_DEVICES=str(args.gpu), OMP_NUM_THREADS='2',
                       MKL_NUM_THREADS='2', MAX_JOBS='2', PYTHONUNBUFFERED='1')
    command = [sys.executable, '-m', 'isaacgymenvs.train', 'task=wuji_demo_aligned',
               'hand=wuji_paper', 'object=knife_wuji_demo_aligned', 'train=wujiDemoAlignedSAPG',
               f'num_envs={args.envs}', f'max_iterations={args.epochs}', f'experiment={run.name}',
               f'train.params.config.expl_coef_block_size={args.envs//5}',
               f'train.params.config.minibatch_size={args.envs*16//5}',
               'headless=True', 'graphics_device_id=-1', 'force_render=False',
               'pipeline=gpu', 'multi_gpu=False', 'seed=20260921']
    state = dict(status='running', started=now(), command=command, pid=os.getpid(),
                 total_steps=args.envs*16*args.epochs, epochs=args.epochs, num_envs=args.envs,
                 physical_gpu=args.gpu, preflight=report, stages=[])
    atomic_json(run / 'pipeline-status.json', state)
    (run / 'pipeline.pid').write_text(str(os.getpid()) + '\n')
    with (run / 'teacher.log').open('w') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    stage = dict(name='teacher', status='running', pid=process.pid, started=now())
    state['stages'].append(stage)
    atomic_json(run / 'pipeline-status.json', state)
    print('teacher started', process.pid, run, flush=True)
    while True:
        code = process.poll()
        pending = [p for p in sorted((run / 'evaluation/inbox').glob('epoch_*.json'))
                   if not (run / 'evaluation' / p.stem / 'result.json').exists()]
        if pending:
            for old in pending[:-1]:
                atomic_json(run / 'evaluation' / old.stem / 'result.json',
                            dict(status='skipped', reason='Newer immutable checkpoint available'))
            evaluate(run, json.loads(pending[-1].read_text()), environment)
        elif code is not None:
            stage.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
            state.update(status=stage['status'], finished=now())
            atomic_json(run / 'pipeline-status.json', state)
            raise SystemExit(code)
        else:
            time.sleep(10)


if __name__ == '__main__':
    main()
