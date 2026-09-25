"""Run the declared replay/current pair from a verified immutable source copy."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root = Path(__file__).resolve().parents[1]
    assert root.name.startswith('artgym-pinned-student-replay-')
    manifest = json.loads((root/'pinned-manifest.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
    base = root/'runs/wuji-goal'
    check = base/'diagnostics/replay-buffer-cuda-check'
    report = json.loads((check/'report.json').read_text())
    status = json.loads((check/'status.json').read_text())
    assert report['status'] == 'passed' and status['returncode'] == 0
    for name, digest in report['source_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest
    directory = base/'diagnostics/student-replay-pair-seed60-v2'
    directory.mkdir(exist_ok=True)
    assert not (directory/'status.json').exists()
    state = dict(status='preflights_then_training', started=now(), root=str(root), processes=[],
                 source_manifest_sha256=hashlib.sha256((root/'pinned-manifest.json').read_bytes()).hexdigest())
    children = []
    for kind, gpu in [('current', 3), ('replay', 2)]:
        spec = base/('student-bridge3-pure250-%s500-seed60-v2-spec.json' % kind)
        env = runtime_environment(dict(project=str(root), python=sys.executable), gpu)
        log = (directory/(kind+'-launcher.log')).open('w')
        child = subprocess.Popen([sys.executable, '-m', 'scripts.run_wuji_student_from_spec', '--spec', str(spec)],
                                 cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        log.close()
        children.append(child)
        state['processes'].append(dict(kind=kind, gpu=gpu, pid=child.pid, spec_sha256=hashlib.sha256(spec.read_bytes()).hexdigest()))
    atomic_json(directory/'status.json', state)
    for child, item in zip(children, state['processes']):
        item['returncode'] = child.wait()
        item['finished'] = now()
        atomic_json(directory/'status.json', state)
    state.update(status='completed' if all(x['returncode'] == 0 for x in state['processes']) else 'failed', finished=now())
    atomic_json(directory/'status.json', state)
    if state['status'] == 'failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
