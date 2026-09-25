"""Wait for GPU4's student run, check three-grasp wiring, then train and audit."""
import json
import subprocess
import sys
import time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import runtime_environment, atomic_json, now


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    path = base / 'bridge3-pipeline-preparation.json'
    assert not path.exists(), 'Preserve prior preparations'
    state = dict(status='waiting_for_predecessor', started=now(), owner='eight', gpu=4,
                 predecessor='wuji_student_near5cp50_warm200_seed31_v1')
    atomic_json(path, state)
    previous = root / 'runs' / state['predecessor'] / 'pipeline-status.json'
    deadline = time.monotonic() + 14400
    while True:
        pre = json.loads(previous.read_text())
        if pre['status'] == 'completed':
            break
        if pre['status'] == 'failed':
            raise RuntimeError('Predecessor failed; preserve it and review before new training')
        if time.monotonic() > deadline:
            raise TimeoutError('Predecessor did not complete in four hours')
        state['heartbeat'] = now()
        atomic_json(path, state)
        time.sleep(20)
    env = runtime_environment(dict(project=str(root), python=sys.executable), 4)
    out = base / 'diagnostics/bridge3-hemisphere-runtime'
    out.mkdir(exist_ok=False)
    command = [sys.executable, '-m', 'scripts.check_wuji_bridge3_hemisphere_runtime', '--output', str(out)]
    with (out / 'worker.log').open('w') as log:
        child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        record = dict(status='running', started=now(), pid=child.pid, command=command, owner='eight', gpu=4)
        atomic_json(out / 'status.json', record)
        code = child.wait()
    record.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
    atomic_json(out / 'status.json', record)
    if code:
        state.update(status='failed', returncode=code, finished=now())
        atomic_json(path, state)
        raise SystemExit(code)
    name = 'wuji_bridge3_cp50_seed45_v1'
    audit_command = [sys.executable, '-m', 'scripts.run_wuji_goal_audits', '--queue',
                     str(base / ('audit-queue-' + name + '.json')), '--gpu', '4', '--checkpoint-wait-seconds', '21600']
    with (base / 'diagnostics/bridge3-audits.log').open('w') as log:
        audit = subprocess.Popen(audit_command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
    state.update(status='preflight_then_training', audit_pid=audit.pid, audit_command=audit_command)
    atomic_json(path, state)
    code = subprocess.call([sys.executable, '-m', 'scripts.run_reference_experiment', '--manifest',
                            'wuji_bridge3_suite.json', '--name', name], cwd=root, env=env)
    state.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
    atomic_json(path, state)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
