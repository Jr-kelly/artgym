"""Bounded precision student pilot with real preflight and frozen-teacher audit."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'runs/wuji_student_precision125_pilot_v1'
TEACHER = ROOT/'runs/wuji_acq_precision_near01_v1/evaluation/monitor/policies/epoch_000125.pth'
EXPECTED = '85ba4a542b7b9c06ff03a288eb2749d1ab061a5787270f9d6ac8cf568fc6aa15'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', default=RUN.name)
    parser.add_argument('--updates', type=int, default=100)
    parser.add_argument('--student-checkpoint', type=Path)
    parser.add_argument('--seed', type=int, default=20261005)
    parser.add_argument('--gpu', type=int, default=2)
    args = parser.parse_args()
    if Path(args.run_name).name != args.run_name or args.updates <= 0:
        raise ValueError('A run basename and positive update budget are required')
    run = ROOT/'runs'/args.run_name
    source_student = None
    if args.student_checkpoint:
        args.student_checkpoint = args.student_checkpoint.resolve()
        source_student = dict(path=str(args.student_checkpoint),
            sha256=hashlib.sha256(args.student_checkpoint.read_bytes()).hexdigest(),
            optimizer='Fresh Adam; only student encoder weights are restored')
    run.mkdir(parents=True, exist_ok=True)
    lock = (run/'pipeline.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state_path = run/'pipeline-status.json'
    if state_path.exists():
        raise RuntimeError('Pilot already exists; preserve its history')
    gate = json.loads((ROOT/'runs/wuji-goal/verification/precision-near01-cp125-perturb-small/report.json').read_text())
    teacher_hash = hashlib.sha256(TEACHER.read_bytes()).hexdigest()
    if (teacher_hash != EXPECTED or gate['checkpoint_sha256'] != EXPECTED or
            gate['successful_trials'] != 100 or gate['strict_first_cycle_trials'] != 100):
        raise RuntimeError('Teacher checkpoint or independent development audit gate failed')
    state = dict(status='preflight', started=now(), host='four', gpu=args.gpu, stages=[],
                 teacher_sha256=teacher_hash, budget_updates=args.updates, num_envs=1024,
                 source_student=source_student, seed=args.seed,
                 launcher_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 purpose='On-policy latent distillation with continuous precise manipulation and full initial perturbations; same-grasp pilot only.')
    atomic_json(state_path, state)
    env = runtime_environment(dict(project=str(ROOT), python=sys.executable), args.gpu)
    for stage, updates in [('preflight', 3), ('distilling', args.updates)]:
        out = run/'preflight' if stage == 'preflight' else run
        out.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, '-m', 'isaacgymenvs.distill', '--checkpoint', str(TEACHER),
                   '--task', 'wuji_acquisition_precision_student', '--train', 'wujiAcquisitionSAPG',
                   '--hand', 'wuji_paper', '--object', 'knife_wuji_precision_near01',
                   '--num-envs', '1024', '--updates', str(updates), '--rollout-steps', '16',
                   '--lr', '0.0001', '--cosine-coef', '0.1', '--deterministic',
                   '--expl-block-idx', '0', '--headless', '--graphics-device-id', '-1',
                   '--save-every-updates', '1' if stage == 'preflight' else '25',
                   '--save-best-after-updates', '25', '--grasp-split', 'train', '--seed', str(args.seed),
                   '--output-checkpoint', str(out/'student.pth'), '--audit-output-dir', str(out/'runtime-audit')]
        if args.student_checkpoint:
            command += ['--student-checkpoint', str(args.student_checkpoint)]
        with (out/'distillation.log').open('w') as log:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT)
            record = dict(stage=stage, status='running', pid=child.pid, command=command, started=now())
            state['stages'].append(record)
            state['status'] = stage
            atomic_json(state_path, state)
            code = child.wait()
        record.update(returncode=code, finished=now(), status='completed' if code == 0 else 'failed')
        if code == 0:
            audit = json.loads((out/'runtime-audit/runtime-audit.json').read_text())
            if audit['status'] != 'verified' or audit['completed_updates'] != updates:
                record['status'] = 'failed'
                record['error'] = 'Runtime audit incomplete'
                code = 1
        if code:
            state.update(status='failed', finished=now())
            atomic_json(state_path, state)
            raise SystemExit(code)
        atomic_json(state_path, state)
    state.update(status='completed', finished=now())
    atomic_json(state_path, state)


if __name__ == '__main__':
    main()
