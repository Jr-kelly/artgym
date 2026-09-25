"""Check the two-grasp curriculum, then queue its bounded reference runner."""
import json
import subprocess
import sys
import time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import runtime_environment, atomic_json, now


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    env = runtime_environment(dict(project=str(root), python=sys.executable), 2)
    # This preceding diagnostic is on the same host/GPU. Waiting here avoids
    # stacking another small simulator while it is still measuring contacts.
    predecessor = base / 'diagnostics/single24-scripted-perturb100/status.json'
    deadline = time.monotonic() + 2100
    while True:
        status = json.loads(predecessor.read_text())
        if status['status'] in ['completed', 'failed']:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError('Prior diagnostic is not terminal; no duplicate or overlapping launch')
        time.sleep(15)
    out = base / 'diagnostics/bridge2-hemisphere-runtime'
    out.mkdir(exist_ok=False)
    command = [sys.executable, '-m', 'scripts.check_wuji_bridge_hemisphere_runtime', '--output', str(out)]
    record = dict(status='running', owner='four', gpu=2, started=now(), command=command)
    with (out / 'worker.log').open('w') as log:
        child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT)
        record['pid'] = child.pid
        atomic_json(out / 'status.json', record)
        try:
            code = child.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = 124
    record.update(status='completed' if code == 0 else 'failed', finished=now(), returncode=code)
    atomic_json(out / 'status.json', record)
    if code:
        raise SystemExit(code)
    command = [sys.executable, '-m', 'scripts.run_reference_experiment', '--manifest', 'wuji_bridge2_suite.json',
               '--name', 'wuji_bridge2_cp50_seed36_v1']
    raise SystemExit(subprocess.call(command, cwd=root, env=env))


if __name__ == '__main__':
    main()
