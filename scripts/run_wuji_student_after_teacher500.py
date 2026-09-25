"""After the fixed teacher-only baseline, adapt its encoder on student rollouts.

This is a new bounded continuation with fresh Adam and fresh simulator state,
not a bitwise resume or a matched 500-update comparison. The baseline and the
ongoing warm200 experiment remain intact. Every new checkpoint is evaluated
with the same independent fixed-clock criteria.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    parent_name = 'wuji_student_near5cp50_teacher500_seed31_v1'
    name = 'wuji_student_near5cp50_teacher500_then_student500_seed40_v1'
    state_path = base / 'student-after-teacher500-preparation.json'
    if state_path.exists():
        raise RuntimeError('A prior continuation already exists; preserve it')
    state = dict(status='waiting_for_predecessor', started=now(), owner='four', gpu=1,
                 scope=__doc__, predecessor=parent_name, run=name)
    atomic_json(state_path, state)
    try:
        deadline = time.monotonic() + 14400
        while True:
            previous = json.loads((root / 'runs' / parent_name / 'pipeline-status.json').read_text())
            if previous['status'] == 'completed':
                break
            if previous['status'] == 'failed':
                raise RuntimeError('Teacher-only baseline failed; do not continue an unverified artifact')
            if time.monotonic() >= deadline:
                raise TimeoutError('Predecessor did not finish in four hours')
            state['heartbeat'] = now()
            atomic_json(state_path, state)
            time.sleep(20)
        # Import only for checkpoint inspection; no simulator is made here.
        import torch
        source = root / 'runs' / parent_name / 'student_update0500.pth'
        payload = torch.load(source, map_location='cpu')
        meta = payload['distill_meta']
        spec = json.loads((base / 'student-near5cp50-teacher500-spec.json').read_text())
        assert meta['teacher_checkpoint_sha256'] == spec['teacher_sha256']
        assert meta['teacher_rollout_updates'] == meta['updates'] == 500
        assert all(meta[key] == spec[key] for key in ['task', 'hand', 'object'])
        assert all(torch.isfinite(x).all() for x in payload['student_encoder_state_dict'].values())
        init = base / 'frozen-candidates/student-near5cp50-teacher500-update500'
        init.mkdir(exist_ok=False)
        shutil.copy2(source, init / 'student.pth')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == hashlib.sha256((init / 'student.pth').read_bytes()).hexdigest()
        atomic_json(init / 'manifest.json', dict(status='frozen_initialization', created=now(),
                    source=str(source.relative_to(root)), sha256=digest,
                    parent_completed=True, all_encoder_tensors_finite=True, teacher_sha256=spec['teacher_sha256']))
        spec.update(run=name, teacher_rollout_updates=0, seed=20261040,
                    student_checkpoint=str((init / 'student.pth').relative_to(root)),
                    student_checkpoint_sha256=digest,
                    purpose=__doc__ + ' Additional500updates x1024envs x16steps, LR1e-4, latentMSE+.1cosine; frozenactor and normalizers. Allrolloutactionsfromstudent. Five actualpreflightupdates verify the loadedencoder and frozenstate before formal launch.')
        spec_path = base / 'student-near5cp50-after-teacher500-spec.json'
        atomic_json(spec_path, spec)
        old_jobs = json.loads((base / 'audit-queue-student-near5cp50-teacher500.json').read_text())
        jobs = []
        for old in old_jobs:
            text = json.dumps(old).replace(parent_name, name).replace('student-near5cp50-teacher500-cp', 'student-near5cp50-after-teacher500-cp')
            jobs.append(json.loads(text))
        queue = base / 'audit-queue-student-near5cp50-after-teacher500.json'
        atomic_json(queue, jobs)
        environment = runtime_environment(dict(project=str(root), python=sys.executable), 1)
        with (base / 'diagnostics/student-after-teacher500-audits.log').open('w') as log:
            audits = subprocess.Popen([sys.executable, '-m', 'scripts.run_wuji_goal_audits', '--queue', str(queue),
                '--gpu', '1', '--checkpoint-wait-seconds', '21600'], cwd=root, env=environment,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        state.update(status='running_preflight_then_training', source_student_sha256=digest, audit_queue_pid=audits.pid,
                     spec=str(spec_path.relative_to(root)), spec_sha256=hashlib.sha256(spec_path.read_bytes()).hexdigest())
        atomic_json(state_path, state)
        code = subprocess.call([sys.executable, '-m', 'scripts.run_wuji_student_from_spec', '--spec', str(spec_path)],
                               cwd=root, env=environment)
        state.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
        atomic_json(state_path, state)
        if code:
            raise SystemExit(code)
    except Exception as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        atomic_json(state_path, state)
        raise


if __name__ == '__main__':
    main()
