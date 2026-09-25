"""Run a bounded, hashed teacher/student evaluation queue under one GPU lease."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    assert os.uname().nodename == spec['hostname']
    root, pin = Path(spec['root']), Path(__file__).resolve().parents[1]
    out = root / spec['output']
    out.mkdir(parents=True, exist_ok=False)
    state = dict(status='waiting_for_gpu', started=now(), pid=os.getpid(),
                 spec=spec, spec_sha256=hashlib.sha256(args.spec.read_bytes()).hexdigest(), stages=[])
    atomic_json(out/'status.json', state)
    lease, child = None, None
    try:
        for filename, digest in spec['artifact_sha256'].items():
            assert hashlib.sha256((root/filename).read_bytes()).hexdigest() == digest, filename
        for filename, digest in spec['source_sha256'].items():
            assert hashlib.sha256((pin/filename).read_bytes()).hexdigest() == digest, filename
        deadline = time.monotonic() + 7200
        while lease is None:
            assert time.monotonic() < deadline, 'No free GPU within two hours'
            lease = acquire_evaluation_gpu(spec['gpu'])
            if lease is not None:
                used = int(subprocess.check_output(['nvidia-smi', '-i', str(spec['gpu']),
                    '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True).strip())
                if used >= 1000:
                    lease.close()
                    lease = None
            if lease is None:
                state.update(heartbeat=now())
                atomic_json(out/'status.json', state)
                time.sleep(10)
        for stage in spec['stages']:
            stage_out = root/stage['output']
            stage_out.mkdir(parents=True, exist_ok=False)
            command = [sys.executable, '-m', stage['module'], '--output', str(stage_out)] + stage['args']
            environment = runtime_environment(dict(project=str(pin), python=sys.executable), spec['gpu'])
            if '--video' in stage['args']:
                # Vulkan does not apply CUDA_VISIBLE_DEVICES remapping. Use
                # the same physical index for both APIs, as the RGB runner does.
                environment.pop('CUDA_VISIBLE_DEVICES', None)
                environment['VK_ICD_FILENAMES'] = spec.get('vulkan_icd', '/etc/vulkan/icd.d/nvidia_icd.json')
                environment.update(spec.get('launch_environment', {}))
                if spec.get('runtime_library_paths'):
                    environment['LD_LIBRARY_PATH'] = ':'.join(spec['runtime_library_paths']) + ':' + environment.get('LD_LIBRARY_PATH', '')
                command += ['--physical-gpu-index', str(spec['gpu'])]
            with (stage_out/'run.log').open('w') as log:
                child = subprocess.Popen(command, cwd=pin,
                    env=environment,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    pass_fds=(lease.fileno(),), start_new_session=True)
            row = dict(name=stage['name'], pid=child.pid, command=command,
                       status='running', started=now())
            state['stages'].append(row)
            state.update(status=stage['name'], heartbeat=now())
            atomic_json(out/'status.json', state)
            atomic_json(stage_out/'status.json', row)
            while child.poll() is None:
                state.update(heartbeat=now())
                atomic_json(out/'status.json', state)
                time.sleep(10)
            row.update(status='completed' if child.returncode == 0 else 'failed',
                       returncode=child.returncode, finished=now())
            atomic_json(stage_out/'status.json', row)
            atomic_json(out/'status.json', state)
            assert child.returncode == 0, row
            assert (stage_out/'report.json').is_file()
        state.update(status='completed', finished=now())
    except BaseException as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        raise
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        if lease is not None:
            lease.close()
        atomic_json(out/'status.json', state)


if __name__ == '__main__':
    main()
