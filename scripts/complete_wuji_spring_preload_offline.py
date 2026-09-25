"""Finish the correctly framed preload probe after a separately verified roundoff audit.

Original failed exits and traces remain unchanged. Select only on the 33 training
grasps, then run every one of the five held-out grasps with the frozen setting.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--gpu', type=int, default=5)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    p = args.directory.resolve()
    assert json.loads((p/'geometry-verification.json').read_text())['status'] == 'passed'
    assert json.loads((p/'roundoff-followup-status.json').read_text())['returncode'] == 0
    manifest = json.loads((p/'train/manifest.json').read_text())
    report_path = p/'train/static/offline-report.json'
    report = json.loads(report_path.read_text())
    assert report['status'] == 'verified_offline' and report['num_envs'] == 297
    assert report['initial_state_sha256'] == manifest['states_sha256']
    rows = []
    for i, setting in enumerate(manifest['settings']):
        records = report['records'][33*i:33*(i+1)]
        meta = manifest['records'][33*i:33*(i+1)]
        rows.append(dict(setting_index=i, setting=setting,
                         stable20s=sum(v['stable20s'] for v in records),
                         stable2s=sum(v['stable2s'] for v in records),
                         falls=sum(v['fall'] for v in records),
                         mean_target_shift_l2=sum(v['target_shift_l2'] for v in meta)/33))
    chosen = min(rows, key=lambda v:(-v['stable20s'], v['mean_target_shift_l2'], v['setting_index']))
    selection = dict(status='selected_on_training_only', selected_utc=now(),
                     setting=chosen['setting'], selected_index=chosen['setting_index'],
                     training_results=rows, source_report=str(report_path.relative_to(root)),
                     source_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                     selection_rule=manifest['selection_rule'], scope=__doc__)
    assert not (p/'selection.json').exists()
    atomic_json(p/'selection.json', selection)
    state = dict(status='running', started=now(), training_selected=chosen, stages=[], scope=__doc__)
    status = p/'offline-completion-status.json'
    atomic_json(status, state)
    env = runtime_environment(dict(project=str(root), python=sys.executable), args.gpu)

    def run(name, arguments):
        with (p/(name+'.log')).open('w') as log:
            child = subprocess.Popen([sys.executable]+arguments, cwd=root, env=env,
                                     stdout=log, stderr=subprocess.STDOUT)
        item = dict(name=name, pid=child.pid, started=now(), command=arguments, status='running')
        state['stages'].append(item)
        atomic_json(status, state)
        try:
            code = child.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(); code=124
        item.update(status='completed' if code==0 else 'failed', returncode=code, finished=now())
        atomic_json(status, state)
        return code

    try:
        validation = p/'validation'
        assert run('prepare_validation', ['-m', 'scripts.prepare_wuji_spring_preload',
                   '--output', str(validation), '--selection', str(p/'selection.json')]) == 0
        code = run('audit_validation', ['-m', 'scripts.audit_wuji_static_grasp', '--hand',
                   'wuji_paper_official_actuator', '--object', 'knife_wuji_fingertip_precision000',
                   '--initial-states', str(validation/'initial_states.npy'),
                   '--output', str(validation/'static')])
        result_path = validation/'static/report.json'
        if code:
            # This helper reconstructs every transition and rejects unexplained
            # target changes; it does not merely increase the live tolerance.
            assert code == 1 and (validation/'static/trace.npz').exists()
            assert run('validation_roundoff', ['-m', 'scripts.audit_wuji_static_roundoff',
                       '--directory', str(validation)]) == 0
            result_path = validation/'static/offline-report.json'
        result = json.loads(result_path.read_text())
        assert result['num_envs'] == 5 and result['recorded_steps'] == 600
        state.update(status='completed', finished=now(), validation_report=str(result_path.relative_to(root)),
                     validation_stable20s=sum(row['stable20s'] for row in result['records']),
                     validation_falls=sum(row['fall'] for row in result['records']))
    except Exception as exc:
        state.update(status='failed', finished=now(), error=repr(exc))
        atomic_json(status, state)
        raise
    atomic_json(status, state)
    print(json.dumps(state), flush=True)


if __name__ == '__main__':
    main()
