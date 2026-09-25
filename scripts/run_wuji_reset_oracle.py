"""Execute a predeclared, frozen, matched-batch privileged diagnosis locally."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--spec', type=Path, required=True)
    args = p.parse_args()
    spec = json.loads(args.spec.read_text())
    root, pin = Path(spec['root']), Path(__file__).resolve().parents[1]
    out = root/spec['output']
    assert out.is_dir() and not (out/'status.json').exists()
    for item in [spec['artifact'], spec['initial_states']]:
        assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest() == item['sha256']
    state = dict(status='starting', started=now(), spec=spec, stages=[])
    atomic_json(out/'status.json', state)
    child = None
    try:
        for stage in spec['stages']:
            cmd = [sys.executable, '-m', 'scripts.eval_wuji_reset_oracle', '--artifact', str(root/spec['artifact']['path']),
                   '--initial-states', str(root/spec['initial_states']['path']), '--output', str(out/stage['name']),
                   '--seconds', str(stage['seconds']), '--feedback', stage['feedback'],
                   '--evaluation-seed', str(spec['evaluation_seed']), '--initial-state-rows']+list(map(str, stage['initial_state_rows']))
            with (out/(stage['name']+'.log')).open('w') as log:
                child = subprocess.Popen(cmd, cwd=pin, env=runtime_environment(dict(project=str(pin), python=sys.executable), 0),
                                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            row = dict(name=stage['name'], status='running', started=now(), pid=child.pid, command=cmd)
            state['stages'].append(row)
            state['status'] = 'evaluating'
            atomic_json(out/'status.json', state)
            code = child.wait()
            row.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
            atomic_json(out/'status.json', state)
            assert code == 0, row
            audit = json.loads((out/stage['name']/'oracle-audit.json').read_text())
            assert audit['status'] == 'passed' and audit['model_unchanged'] and audit['current_truth_actor_input']
        state.update(status='completed', finished=now())
    except BaseException as exc:
        state.update(status='failed', finished=now(), error=repr(exc))
        if child and child.poll() is None:
            child.terminate()
            child.wait(timeout=20)
        raise
    finally:
        atomic_json(out/'status.json', state)


if __name__ == '__main__':
    main()
