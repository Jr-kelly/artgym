"""Pinned 20/60-second training pair after the four-host student MSE trial."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    assert root.name.startswith('artgym-pinned-bridge3-horizon-')
    base = root / 'runs/wuji-goal'
    record_path = base / 'diagnostics/bridge3-horizon-pair-launch.json'
    assert not record_path.exists()
    source = json.loads((root / 'pinned-manifest.json').read_text())
    for path, digest in source.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
    env = runtime_environment(dict(project=str(root), python=sys.executable), 1)
    state = dict(status='waiting_for_student', started=now(), owner='four', gpu=1,
                 pinned_root=str(root), source_manifest_sha256=hashlib.sha256((root/'pinned-manifest.json').read_bytes()).hexdigest())
    atomic_json(record_path, state)
    deadline = time.monotonic()+10800
    while time.monotonic() < deadline:
        p = root / 'runs/wuji_student_near5cp50_teacher500_then_mse2lr500_seed40_v1/pipeline-status.json'
        prior = json.loads(p.read_text())
        if prior['status'] == 'completed':
            break
        if prior['status'] == 'failed':
            raise RuntimeError('The preceding student experiment failed')
        time.sleep(20)
    else:
        raise TimeoutError('Predecessor did not finish in three hours')
    for maximum in [600, 1800]:
        output = base / ('diagnostics/bridge3-episode-boundary%d-seed58' % maximum)
        command = [sys.executable, '-m', 'scripts.check_wuji_bridge3_episode_duration',
                   '--output', str(output), '--maximum', str(maximum)]
        with output.with_suffix('.log').open('w') as log:
            child = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            state.update(status='boundary_check', maximum=maximum, pid=child.pid)
            atomic_json(record_path, state)
            code = child.wait()
        output.mkdir(exist_ok=True)
        atomic_json(output / 'status.json', dict(status='completed' if code == 0 else 'failed', returncode=code, finished=now()))
        if code:
            state.update(status='failed', returncode=code, finished=now())
            atomic_json(record_path, state)
            raise SystemExit(code)
    for seconds in [60, 20]:
        for path, digest in source.items():
            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
        name = 'wuji_bridge3_horizon%d_cp25_seed58_pinned_v1' % seconds
        state.update(status='preflight_then_training', run=name)
        atomic_json(record_path, state)
        code = subprocess.call([sys.executable, '-m', 'scripts.run_reference_experiment',
                                '--manifest', 'wuji_bridge3_horizon_suite.json', '--name', name], cwd=root, env=env)
        if code:
            state.update(status='failed', returncode=code, finished=now())
            atomic_json(record_path, state)
            raise SystemExit(code)
    state.update(status='completed', finished=now())
    atomic_json(record_path, state)


if __name__ == '__main__':
    main()
