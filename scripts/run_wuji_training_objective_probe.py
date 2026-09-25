"""Run a finite, frozen-policy reward/endpoint diagnostic on an idle GPU."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pin = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    env = runtime_environment(dict(project=str(pin), python=sys.executable), 1)
    base = args.root/'runs/wuji-goal/frozen-candidates'
    candidates = {
        'smallnoise_cp25': base/'student-actorrl-sigmaquarter-broad0-seed62-cp25/actor.pth',
        'smallnoise_cp100': base/'student-actorrl-sigmaquarter-broad0-seed62-cp100/actor.pth',
        'pose1_cp100': args.root/'runs/wuji_student_actorrl_smallcp25_pose1_noramp_seed64_v1/checkpoints/epoch_000100.pth'}
    assert all(p.exists() for p in candidates.values())
    trials = [('preflight', candidates['smallnoise_cp25'], 'mean', 320)]
    trials += [(key+'_'+mode, path, mode, 5120) for key, path in candidates.items() for mode in ['mean', 'sample']]
    state = dict(status='running', started=now(), owner='four', gpu=1, stages=[])
    atomic_json(args.output/'status.json', state)
    try:
        for name, checkpoint, mode, count in trials:
            output = args.output/name
            command = [sys.executable, '-m', 'scripts.probe_wuji_training_objective',
                '--checkpoint', str(checkpoint), '--output', str(output),
                '--mode', mode, '--num-envs', str(count)]
            with (args.output/(name+'.log')).open('w') as log:
                process = subprocess.Popen(command, cwd=pin, env=env, stdout=log, stderr=subprocess.STDOUT)
                stage = dict(name=name, pid=process.pid, command=command, status='running', started=now())
                state['stages'].append(stage)
                atomic_json(args.output/'status.json', state)
                code = process.wait()
            stage.update(returncode=code, status='completed' if code == 0 else 'failed', finished=now())
            atomic_json(args.output/'status.json', state)
            assert code == 0, name
            report = json.loads((output/'report.json').read_text())
            assert report['physics_transitions'] == count*600
            assert report['model_unchanged'] and report['encoder_unchanged']
        state.update(status='completed', finished=now())
        atomic_json(args.output/'status.json', state)
    except BaseException as error:
        state.update(status='failed', error=repr(error), finished=now())
        atomic_json(args.output/'status.json', state)
        raise


if __name__ == '__main__':
    main()
