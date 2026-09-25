"""Gate counterfactual observation on physical noninterference, then diagnose CP100."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu', type=int, required=True)
    args = parser.parse_args()
    directory = ROOT / 'runs/wuji-goal/diagnostics/bridge3-encoder-cp100-diagnostic'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'executed-launcher.py').write_bytes(Path(__file__).read_bytes())
    atomic_json(directory / 'status.json', dict(status='gating', started=now(), gpu=args.gpu))

    def job(driver, cp, rows, suffix, driver_only=False):
        paths = ['runs/wuji_student_bridge3cp25_%s1000_seed57_v1/student_update%04d.pth' % (kind, cp)
                 for kind in ['pure', 'controller']]
        return dict(name='bridge3-encoder-%s-%s' % (driver, suffix),
                    module='scripts.probe_wuji_bridge3_student_latents',
                    checkpoint='runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth',
                    required_artifacts=paths,
                    args=['--plain-student', paths[0], '--controller-student', paths[1],
                          '--initial-states', 'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy',
                          '--initial-state-rows'] + [str(x) for x in rows] +
                         ['--driver', driver, '--seed', '20261057'] + (['--driver-only'] if driver_only else []))

    def run_queue(jobs, name):
        queue = directory / (name + '.json')
        atomic_json(queue, jobs)
        code = subprocess.call([sys.executable, '-m', 'scripts.run_wuji_goal_audits', '--queue', str(queue),
                                '--gpu', str(args.gpu), '--checkpoint-wait-seconds', '21600'], cwd=ROOT)
        assert code == 0, (name, code)
        for item in jobs:
            status = json.loads((ROOT / 'runs/wuji-goal/verification' / item['name'] / 'status.json').read_text())
            assert status['status'] == 'completed' and status['returncode'] == 0, (item['name'], status)

    gates = [job(driver, 25, [0, 100, 200], 'gate-cp25-' + mode, mode == 'driver-only')
             for driver in ['teacher', 'plain', 'controller'] for mode in ['driver-only', 'observed']]
    run_queue(gates, 'gate-queue')
    comparisons = []
    for driver in ['teacher', 'plain', 'controller']:
        folder = ROOT / 'runs/wuji-goal/verification'
        base = folder / ('bridge3-encoder-%s-gate-cp25-driver-only' % driver)
        observed = folder / ('bridge3-encoder-%s-gate-cp25-observed' % driver)
        matched = {}
        for name in ['trace.npz', 'encoder_error_trace.npz']:
            a, b = np.load(base / name), np.load(observed / name)
            for key in a.files:
                assert key in b.files and np.array_equal(a[key], b[key], equal_nan=True), (driver, name, key)
                matched[name + ':' + key] = list(a[key].shape)
        comparisons.append(dict(driver=driver, exact_match=True, matched_shapes=matched))
    atomic_json(directory / 'noninterference.json', dict(status='passed', finished=now(), comparisons=comparisons,
                scope='Same seeded3env600steps, driver action, RNN sums and physical traces identical; no assertion of task success.'))
    atomic_json(directory / 'status.json', dict(status='diagnosing', gating_passed=True, gpu=args.gpu, updated=now()))
    rows = [g + i for g in [0, 100, 200] for i in range(24)]
    jobs = [job(driver, 100, rows, 'cp100-development72') for driver in ['teacher', 'plain', 'controller']]
    run_queue(jobs, 'diagnostic-queue')
    atomic_json(directory / 'status.json', dict(status='completed', gating_passed=True, gpu=args.gpu, finished=now()))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        directory = ROOT / 'runs/wuji-goal/diagnostics/bridge3-encoder-cp100-diagnostic'
        directory.mkdir(parents=True, exist_ok=True)
        atomic_json(directory / 'failure.json', dict(finished=now(), error=repr(error)))
        raise
