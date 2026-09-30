"""Frozen, serial local rendering fallback with the same global GPU ledger.

No training or quantitative final evaluation can run through this entry point.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile
from pathlib import Path

from scripts.record_wuji_recovery import D, R, record
from scripts.monitor_wuji_checkpoints import runtime_environment


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', choices=['S2', 'S5', 'F'], required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    assert args.name.startswith('local-') and '/' not in args.name and '..' not in args.name
    assert 0 < args.timeout <= 1800
    frozen_path = D / 'final-freeze.json'
    frozen = json.loads(frozen_path.read_text())
    assert subprocess.check_output(['git', 'show', 'HEAD:research/artmanip-recovery-20260930/final-freeze.json'], cwd=R) == frozen_path.read_bytes()
    subprocess.run(['python3', '-m', 'scripts.status_wuji_recovery'], cwd=R,
                   check=True, stdout=subprocess.DEVNULL)
    state = json.loads((D / 'STATE.json').read_text())
    assert not state['active_jobs'], 'Finish remote final evaluation and prior local jobs first'
    now = datetime.datetime.now(datetime.timezone.utc)
    assert (datetime.datetime.fromisoformat(state['deadline_utc']) - now).total_seconds() >= args.timeout
    assert state['gpu_hours'] + state['unmetered_cuda_preflight_reserve_gpu_hours'] + args.timeout / 3600 <= state['max_gpu_hours']
    # Desktop graphics are not terminated. Reject other compute users on GPU0.
    compute = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], text=True)
    assert not compute.strip(), 'Local GPU0 has an existing compute process'
    gpu = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-gpu=index,name,uuid,memory.used', '--format=csv,noheader'], text=True)
    name = frozen['overall_candidate']
    model = frozen['models'][name]
    assert sha(R / model['path']) == model['sha256']
    video = frozen['video']
    assert sha(R / video['states']) == video['states_sha256']
    assert video['rows'] == [0, 32, 64, 96]
    source = frozen['source_sha']
    pin = R.parent / '.wuji-recovery-local-pins' / source
    if not pin.exists():
        raw = subprocess.check_output(['git', 'archive', source, 'scripts', 'isaacgymenvs', 'rl_games'], cwd=R)
        pin.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=source + '.building-', dir=pin.parent))
        try:
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                archive.extractall(staging)
            for directory in ['caches', 'research', 'runs']:
                (staging / directory).symlink_to(R / directory, target_is_directory=True)
            # Same filesystem; immutable asset hardlinks, as on the H200 pins.
            shutil.copytree(R / 'assets', staging / 'assets', copy_function=os.link)
            (staging / '.source-sha').write_text(source)
            staging.rename(pin)
        finally:
            if staging.exists():shutil.rmtree(staging)
    assert (pin / '.source-sha').read_text() == source
    output = R / 'runs/artmanip-recovery-20260930' / args.name
    assert not output.exists() and not output.with_name(args.name + '-job').exists()
    command = ['PYTHON', '-m', 'scripts.evaluate_wuji_recovery', '--checkpoint', model['path'],
               '--task', 'wuji_artmanip_reference' if name.startswith('rl') else 'wuji_multigrasp',
               '--hand', 'wuji_paper_official_actuator', '--object', 'knife_wuji_bridge3_20260922',
               '--initial-states', video['states'], '--initial-state-rows', *map(str, video['rows']),
               '--output', str(output), '--seed', str(frozen['seed']), '--protocol', args.protocol[0],
               '--stage-seconds', '5' if args.protocol == 'S5' else '2', '--video']
    wrapper_name = args.name + '-job'
    registry = D / 'local-jobs'
    registry.mkdir(exist_ok=True)
    assert not (registry / (wrapper_name + '.json')).exists()
    wrapper = [str(args.python), '-m', 'scripts.run_wuji_recovery_job', '--name', wrapper_name,
               '--gpu', '0', '--timeout', str(args.timeout), '--', *command]
    env = runtime_environment(dict(project=str(pin), python=str(args.python)), 0)
    env['WUJI_RECOVERY_FINAL_PHASE'] = '1'
    with output.with_name(args.name + '-launch.log').open('x') as log:
        child = subprocess.Popen(wrapper, cwd=pin, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    spec = dict(name=wrapper_name, pid=child.pid, gpu=0, host='local',
                hostname=socket.gethostname(), gpu_snapshot=gpu, source_sha=source,
                created_utc=now.isoformat(), timeout=args.timeout, final_phase=True,
                status_path=f'runs/artmanip-recovery-20260930/{wrapper_name}/status.json',
                command=wrapper, checkpoint_sha256=model['sha256'],
                freeze_sha256=sha(frozen_path), scope='Separate local simulation video; not final cohort statistics')
    temporary = registry / (wrapper_name + '.tmp')
    temporary.write_text(json.dumps(spec, indent=2) + '\n')
    temporary.rename(registry / (wrapper_name + '.json'))
    record('frozen_local_video_started', **spec,
           next='Use global status tool for local+remote GPU accounting; package and independently rescore video')
    print(json.dumps(spec))


if __name__ == '__main__':
    main()
