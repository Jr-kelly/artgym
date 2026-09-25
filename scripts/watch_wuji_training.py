"""Evaluate immutable teacher snapshots while training continues on four GPUs."""
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


def evaluate_snapshot(run, record, dataset, gpu, instances, timeout):
    epoch = record['epoch']
    folder = run / 'evaluation' / f'epoch_{epoch:06d}'
    folder.mkdir(parents=True, exist_ok=True)
    checkpoint = Path(record['policy_checkpoint'])
    result = dict(record, started=datetime.now(timezone.utc).isoformat(),
                  status='running', instances={}, seed=20260921, randomized=True,
                  episodes_per_grasp=5, selection_split='test grasps of training geometries')
    atomic_json(run / 'evaluation' / 'status.json', result)
    environment = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS='2',
                       MKL_NUM_THREADS='2', MAX_JOBS='2', PYTHONUNBUFFERED='1')
    for key in list(environment):
        if key in ('RANK', 'LOCAL_RANK', 'WORLD_SIZE', 'LOCAL_WORLD_SIZE', 'MASTER_ADDR', 'MASTER_PORT'):
            environment.pop(key)
    for instance in instances:
        summary = folder / f'{instance}.json'
        command = [sys.executable, '-m', 'isaacgymenvs.eval_consecutive',
                   '--checkpoint', str(checkpoint), '--summary-output', str(summary),
                   '--hand', 'wuji_paper', '--object', dataset + '_eval', '--train', 'wujiKnifeSAPG',
                   '--instance-id', instance, '--grasp-split', 'test', '--episodes-per-grasp', '5',
                   '--max-steps', '1200', '--headless', '--graphics-device-id', '-1',
                   '--deterministic', '--randomize', 'True', '--seed', '20260921']
        atomic_json(folder / f'{instance}-command.json', command)
        with (folder / f'{instance}.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, env=environment, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=timeout)
        result['instances'][instance] = json.loads(summary.read_text())
    trials = sum(v['total_trials'] for v in result['instances'].values())
    successes = sum(v['successful_trials'] for v in result['instances'].values())
    result.update(status='completed', finished=datetime.now(timezone.utc).isoformat(),
                  total_trials=trials, successful_trials=successes,
                  execution_success_rate=successes / trials,
                  mean_cycles=sum(v['mean_cycles'] * v['total_trials']
                                  for v in result['instances'].values()) / trials)
    return result


def score(result):
    return result['execution_success_rate'], result['mean_cycles']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--dataset', default='knife_wuji_fingertip')
    parser.add_argument('--gpu', type=int, default=3)
    parser.add_argument('--instances', nargs='+', default=['000', '010', '020'])
    parser.add_argument('--poll-seconds', type=float, default=15)
    parser.add_argument('--timeout-seconds', type=int, default=900)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    manifest = json.loads((ROOT / 'assets/objects' / args.dataset / 'manifest.json').read_text())
    if not set(args.instances) <= set(manifest['train_ids']):
        raise ValueError('Periodic policy selection must exclude held-out geometries')
    evaluation = run / 'evaluation'
    evaluation.mkdir(parents=True, exist_ok=True)
    lock = (evaluation / 'watcher.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (evaluation / 'watcher.pid').write_text(str(os.getpid()) + '\n')
    while True:
        pending = [p for p in sorted((evaluation / 'inbox').glob('epoch_*.json'))
                   if not (evaluation / p.stem / 'result.json').exists()]
        if pending:
            # If evaluation lags, evaluate the newest complete policy first.
            for old in pending[:-1]:
                atomic_json(evaluation / old.stem / 'result.json',
                            dict(status='skipped', reason='newer snapshot available'))
            record = json.loads(pending[-1].read_text())
            target = evaluation / pending[-1].stem / 'result.json'
            try:
                result = evaluate_snapshot(run, record, args.dataset, args.gpu,
                                           args.instances, args.timeout_seconds)
                best_path = evaluation / 'best.json'
                best = json.loads(best_path.read_text()) if best_path.exists() else None
                if best is None or score(result) > score(best):
                    # The inbox policy is immutable and retained; atomically point to it.
                    temporary = evaluation / f'.best.{os.getpid()}'
                    temporary.unlink(missing_ok=True)
                    temporary.symlink_to(os.path.relpath(record['policy_checkpoint'], evaluation))
                    os.replace(temporary, evaluation / 'best.pth')
                    atomic_json(best_path, result)
                atomic_json(evaluation / 'latest.json', result)
            except Exception as error:
                result = dict(record, status='failed', error=repr(error),
                              finished=datetime.now(timezone.utc).isoformat())
                print(f'Evaluation failed at epoch {record["epoch"]}: {error}', flush=True)
            atomic_json(target, result)
            atomic_json(evaluation / 'status.json', result)
            with (evaluation / 'history.jsonl').open('a') as stream:
                stream.write(json.dumps(result) + '\n')
            print(f'Evaluation epoch {record["epoch"]}: {result["status"]}', flush=True)
        if args.once:
            break
        if (evaluation / 'training-finished.json').exists():
            remaining = [p for p in (evaluation / 'inbox').glob('epoch_*.json')
                         if not (evaluation / p.stem / 'result.json').exists()]
            if not remaining:
                break
        time.sleep(args.poll_seconds)


if __name__ == '__main__':
    main()
