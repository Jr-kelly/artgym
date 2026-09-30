"""Require complete, unique frozen physical cells and independently scored trials."""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    freeze_path = root / 'research/artmanip-recovery-20260930/final-freeze.json'
    frozen = json.loads(freeze_path.read_text())
    expected = {(m, p) for m in frozen['models'] for p in frozen['protocols']}
    expected_rows = {(m, p, s) for m, p in expected for s in range(4)}
    code_hashes = {}
    for field, filename in [('source_sha256', 'evaluate_wuji_recovery.py'),
                            ('scorer_sha256', 'wuji_timed_command_metrics.py')]:
        code = subprocess.check_output(['git', 'show', frozen['source_sha'] + ':scripts/' + filename], cwd=root)
        code_hashes[field] = hashlib.sha256(code).hexdigest()
    seen, evidence = set(), []
    for path in sorted((root / 'runs/artmanip-recovery-20260930').glob('*/plan.json')):
        plan = json.loads(path.read_text())
        if plan['states_sha256'] != frozen['final_states']['sha256']:
            continue
        directory = path.parent
        assert (directory / 'completed.json').exists(), 'Incomplete final batch: ' + str(directory)
        assert plan['freeze_sha256'] == sha(freeze_path)
        requested = {(m, p) for m in plan['models'] for p in plan['protocols']}
        results = json.loads((directory / 'results.json').read_text())
        assert len(results) == len(requested)
        actual = set()
        for item in results:
            key = item['model'], item['protocol']
            assert key in requested and key in expected and key not in seen and key not in actual
            report_path = directory / item['directory'] / 'report.json'
            report = json.loads(report_path.read_text())
            assert report == item['report']
            model = frozen['models'][key[0]]
            assert plan['models'][key[0]] == {k: model[k] for k in ['path', 'sha256']}
            assert report['checkpoint_sha256'] == model['sha256'] == sha(root / model['path'])
            assert report['initial_states_sha256'] == frozen['final_states']['sha256']
            assert report['initial_state_rows'] == list(range(512)) and report['num_envs'] == 512
            assert report['control_mode'] == 'privileged_teacher' and report['student_sha256'] is None
            assert all(report[k] == v for k, v in code_hashes.items())
            assert report['hand'] == 'wuji_paper_official_actuator' and report['object'] == 'knife_wuji_bridge3_20260922'
            assert report['action_control']['mode'] == model['interface']
            protocol = report['protocol']
            assert protocol['kind'] == key[1][0]
            assert protocol['hold_steps'] == (45 if key[1] == 'F' else 9)
            assert protocol['goal_tolerance_m'] == (.01 if key[1] == 'F' else .002)
            assert protocol['arrival_used_for_switching'] == (key[1] == 'F')
            if key[1] != 'F':
                assert protocol['stage_steps'] == (150 if key[1] == 'S5' else 60)
            assert report['declared_horizon_steps'] == (1200 if key[1] == 'F' else 600)
            actual.add(key)
            evidence.append(dict(model=key[0], protocol=key[1], report=str(report_path.relative_to(root)),
                                 sha256=sha(report_path)))
        assert actual == requested
        seen |= actual
    assert seen == expected, 'Missing frozen cells: ' + repr(sorted(expected - seen))
    report = json.loads((args.analysis / 'report.json').read_text())
    assert report['independent_rescore'] == 'passed'
    rows = {(r['model'], r['protocol'], r['source']): r for r in report['rows']}
    assert len(rows) == len(report['rows']) and set(rows) == expected_rows
    trials = list(csv.DictReader((args.analysis / 'trials.csv').open()))
    ids = {(r['model'], r['protocol'], int(r['source']), int(r['trial'])) for r in trials}
    assert len(ids) == len(trials) == len(expected_rows) * 128
    assert ids == {(*key, i) for key in expected_rows for i in range(128)}
    for key, row in rows.items():
        group = [r for r in trials if (r['model'], r['protocol'], int(r['source'])) == key]
        assert row['n'] == 128
        for metric, trial_key in [('success', 'success'), ('body_stable', 'body_stable'), ('alive', 'alive')]:
            assert row[metric] == sum(r[trial_key] == 'True' for r in group)
    result = dict(passed=True, freeze_sha256=sha(freeze_path), models=len(frozen['models']),
                  physical_cells=len(expected), source_cells=len(rows), episodes=len(trials),
                  frozen_code_hashes=code_hashes, evidence=evidence,
                  scope='Complete frozen cohort/weight/protocol coverage and independent CSV consistency; no reselection or capability threshold change.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'evidence'}))


if __name__ == '__main__':
    main()
