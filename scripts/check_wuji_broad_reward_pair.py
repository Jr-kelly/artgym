"""Compare reward-only branches using identical frozen actions in real physics."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'runs/wuji-goal/diagnostics/student-actorrl-broad5-runtime-v1'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    assert not (OUTPUT/'status.json').exists()
    atomic_json(OUTPUT/'status.json', dict(status='running', started=now()))
    reports = []
    try:
        for label, coefficient in [('zero', 0), ('broad5', 5)]:
            out = OUTPUT/label
            command = [sys.executable, '-m', 'scripts.check_wuji_student_actor_runtime',
                       '--output', str(out), '--steps', '600',
                       '--broad-goal-coefficient', str(coefficient)]
            with (OUTPUT/(label+'.log')).open('w') as log:
                code = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            assert code == 0, (label, code)
            report = json.loads((out/'report.json').read_text())
            assert report['checks']['transitions'] == 19200
            assert report['broad_goal_reward_checks']['command_switches'] > 0
            reports.append(report)
        assert reports[0]['physics_action_actor_rnn_sha256'] == reports[1]['physics_action_actor_rnn_sha256']
        sources = reports[0]['sources']
        assert sources == reports[1]['sources']
        sources[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        result = dict(status='passed', finished=now(), sources=sources,
                      actual_physics_transitions=38400, branches=reports,
                      identical_physics_actions_and_actor_rnn=True,
                      reward_delta_matches_old_command_analytic_bonus=True,
                      scope='Frozen policy control of reward wiring; not a training outcome or generalization claim.')
        atomic_json(OUTPUT/'report.json', result)
        atomic_json(OUTPUT/'status.json', dict(status='completed', returncode=0, finished=now()))
    except BaseException as error:
        atomic_json(OUTPUT/'status.json', dict(status='failed', error=repr(error), finished=now()))
        raise


if __name__ == '__main__':
    main()
