"""Validate current unchanged control semantics, then compare initialization.

The optional object inertia import flag changed the source hash after the old
gate; this runs physics again and preserves both records instead of bypassing
that gate. Default imported inertia remains identical for both bridge3 runs.
"""
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    name = 'wuji_bridge3_functionalcp100_seed45_v1'
    assert json.loads((root/'runs/wuji_bridge3_cp50_seed45_v1/pipeline-status.json').read_text())['status'] == 'completed'
    path = base/'diagnostics/bridge3-reverse-initialization-launch.json'
    assert not path.exists()
    env = runtime_environment(dict(project=str(root), python=sys.executable), 4)
    out = base/'diagnostics/bridge3-current-source-runtime'
    out.mkdir(exist_ok=False)
    command = [sys.executable, '-m', 'scripts.check_wuji_bridge3_hemisphere_runtime', '--output', str(out)]
    with (out/'worker.log').open('w') as log:
        child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    state = dict(status='runtime_check', started=now(), owner='eight', gpu=4, pid=child.pid, command=command)
    atomic_json(path, state)
    atomic_json(out/'status.json', dict(state, status='running'))
    code = child.wait()
    atomic_json(out/'status.json', dict(state, status='completed' if code == 0 else 'failed', returncode=code, finished=now()))
    if code:
        atomic_json(path, dict(state, status='failed', returncode=code, finished=now()))
        raise SystemExit(code)
    queue = base/('audit-queue-'+name+'.json')
    with (base/'diagnostics/bridge3-reverse-audits.log').open('w') as log:
        audit = subprocess.Popen([sys.executable, '-m', 'scripts.run_wuji_goal_audits', '--queue', str(queue),
            '--gpu', '4', '--checkpoint-wait-seconds', '21600'], cwd=root, env=env,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    state.update(status='preflight_then_training', audit_pid=audit.pid)
    atomic_json(path, state)
    code = subprocess.call([sys.executable, '-m', 'scripts.run_reference_experiment', '--manifest',
        'wuji_bridge3_reverse_suite.json', '--name', name], cwd=root, env=env)
    atomic_json(path, dict(state, status='completed' if code == 0 else 'failed', returncode=code, finished=now()))
    raise SystemExit(code)


if __name__ == '__main__':
    main()
