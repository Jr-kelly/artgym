"""Run boundary checks and a sequential same-GPU two-grasp horizon pair."""
import json
import subprocess
import sys
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    environment = runtime_environment(dict(project=str(root), python=sys.executable), 2)
    for maximum in [600, 1800]:
        output = base / ('diagnostics/bridge2-episode-boundary%d' % maximum)
        command = [sys.executable, '-m', 'scripts.check_wuji_bridge_episode_duration',
                   '--output', str(output), '--maximum', str(maximum)]
        assert not output.exists(), 'Preserve previous checks'
        with (base / ('diagnostics/bridge2-episode-boundary%d.log' % maximum)).open('w') as log:
            child = subprocess.Popen(command, cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT)
            state = dict(status='running', owner='four', gpu=2, started=now(), pid=child.pid, command=command)
            atomic_json(base / ('diagnostics/bridge2-episode-boundary%d-launch.json' % maximum), state)
            code = child.wait()
        state.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
        output.mkdir(exist_ok=True)
        atomic_json(output / 'status.json', state)
        if code:
            raise SystemExit(code)
    for seconds in [60, 20]:
        command = [sys.executable, '-m', 'scripts.run_reference_experiment',
                   '--manifest', 'wuji_bridge2_horizon_suite.json',
                   '--name', 'wuji_bridge2_horizon%d_cp50_seed43_v1' % seconds]
        code = subprocess.call(command, cwd=root, env=environment)
        if code:
            raise SystemExit(code)


if __name__ == '__main__':
    main()
