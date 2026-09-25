"""Package completed command-input results without changing any running experiment."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import time
import json

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fit-audit', type=Path, required=True)
    parser.add_argument('--publisher-sha256', required=True)
    args = parser.parse_args()
    state_path = args.run/'result-packaging-status.json'
    assert not state_path.exists() and not args.output.exists()
    state = dict(status='waiting_for_all_evaluations', started=now(),
        publisher_sha256=args.publisher_sha256, output=str(args.output))
    atomic_json(state_path, state)
    try:
        deadline = time.monotonic()+7200
        while True:
            experiment = json.loads((args.run/'status.json').read_text())
            assert experiment['status'] != 'failed', experiment
            if experiment['status'] == 'completed':
                break
            assert time.monotonic() < deadline, 'Result wait exceeded two hours; no experiment was stopped.'
            state.update(heartbeat=now(), experiment_status=experiment['status'])
            atomic_json(state_path, state)
            time.sleep(30)
        publisher = args.root/'scripts/publish_wuji_command_slider_final.py'
        assert hashlib.sha256(publisher.read_bytes()).hexdigest() == args.publisher_sha256
        cmd = [sys.executable, '-m', 'scripts.publish_wuji_command_slider_final',
            '--run', str(args.run), '--output', str(args.output), '--fit-audit', str(args.fit_audit)]
        with (args.run/'result-packaging.log').open('w') as log:
            child = subprocess.Popen(cmd, cwd=args.root,
                env=runtime_environment(dict(project=str(args.root), python=sys.executable), ''),
                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            state.update(status='rescoring_and_packaging', pid=child.pid, heartbeat=now())
            atomic_json(state_path, state)
            code = child.wait()
        assert code == 0, dict(returncode=code, log=str(args.run/'result-packaging.log'))
        state.update(status='completed', finished=now(), release_upload_pending=True)
        atomic_json(state_path, state)
    except BaseException as error:
        state.update(status='failed', error=repr(error), finished=now())
        atomic_json(state_path, state)
        raise


if __name__ == '__main__':
    main()
