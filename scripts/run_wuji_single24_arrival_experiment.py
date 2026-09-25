"""Run real training-wiring checks before a bounded arrival-acquisition teacher."""
import json
import subprocess
import sys
from pathlib import Path

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    env = runtime_environment(dict(project=str(root), python=sys.executable), 7)
    gates = [
        ('functional-single24-arrival-runtime', 'scripts.check_wuji_single24_arrival_runtime', []),
        ('single24-arrival-positive-clock-gate', 'scripts.check_wuji_training_clock',
         ['--checkpoint', 'runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth',
          '--arrival-control']),
    ]
    for name, module, args in gates:
        out = base / 'diagnostics' / name
        out.mkdir(exist_ok=False)
        command = [sys.executable, '-m', module, '--output', str(out)] + args
        status = dict(status='running', started=now(), command=command, owner='eight', gpu=7)
        with (out / 'worker.log').open('w') as log:
            child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT)
            status['pid'] = child.pid
            atomic_json(out / 'status.json', status)
            try:
                code = child.wait(timeout=900)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
                code = 124
        status.update(status='completed' if code == 0 else 'failed', finished=now(), returncode=code)
        atomic_json(out / 'status.json', status)
        if code:
            raise SystemExit(code)
        assert json.loads((out / 'report.json').read_text())['status'] == 'passed'
    name = 'wuji_single24_scratch_arrival_seed27_v1'
    command = [sys.executable, '-m', 'scripts.run_reference_experiment',
               '--manifest', 'wuji_single24_arrival_suite.json', '--name', name]
    raise SystemExit(subprocess.call(command, cwd=root, env=env))


if __name__ == '__main__':
    main()
