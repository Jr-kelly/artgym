"""Check frozen model/cohort coverage and provenance of independently scored final traces."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', type=Path, default=Path('research/unified-student-20261001/final-freeze.json'))
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    frozen = json.loads(args.freeze.read_text())
    analysis = json.loads((args.analysis / 'report.json').read_text())
    with (args.analysis / 'trials.csv').open() as stream:
        trials = list(csv.DictReader(stream))
    assert analysis['independent_rescore']
    assert sha(Path(frozen['cohort']['path'])) == frozen['cohort']['sha256']
    assert sha(Path('research/unified-student-20261001/INPUTS.md')) == frozen['input_definition_sha256']
    models = [frozen['teacher']] + frozen['models']
    assert len({m['name'] for m in models}) == len(models)
    assert {r['model'] for r in analysis['rows']} == {m['name'] for m in models}
    expected_cells = len(models) * 3 * 4
    assert len(analysis['rows']) == expected_cells
    assert len(trials) == expected_cells * 128
    evidence = []
    for model in models:
        assert sha(Path(model['path'])) == model['sha256']
        for protocol in frozen['protocols']:
            directory = Path(model['evaluation_root']) / (model['name'] + '-' + protocol)
            report = json.loads((directory / 'report.json').read_text())
            assert report['num_envs'] == 512 and report['initial_state_rows'] == list(range(512))
            assert report['initial_states_sha256'] == frozen['cohort']['sha256']
            assert report['checkpoint_sha256'] == frozen['teacher']['sha256']
            student = model['name'] != frozen['teacher']['name']
            assert report['unified_student_sha256'] == (model['sha256'] if student else None)
            assert report['control_mode'] == ('initial_calibration_conditional_student' if student else 'privileged_teacher')
            assert not report['independent_teacher_label_diagnostic']
            for key, value in frozen['evaluation_conditions'].items():
                assert report[key] == value, (model['name'], protocol, key)
            assert report['protocol'] == frozen['protocol_definitions'][protocol]
            trace_hash = sha(directory / 'trace.npz')
            for source in range(4):
                cell = [r for r in analysis['rows'] if (r['model'], r['protocol'], r['source']) == (model['name'], protocol, source)]
                assert len(cell) == 1 and cell[0]['n'] == 128
                assert cell[0]['cohort_sha256'] == frozen['cohort']['sha256']
                assert cell[0]['trace_sha256'] == trace_hash
                selected = [t for t in trials if (t['model'], t['protocol'], int(t['source'])) == (model['name'], protocol, source)]
                assert len(selected) == 128 and {int(t['trial']) for t in selected} == set(range(128))
                assert all(t['cohort_sha256'] == frozen['cohort']['sha256'] for t in selected)
                assert sum(t['success'] == 'True' for t in selected) == cell[0]['success']
                assert sum(t['body_stable'] == 'True' for t in selected) == cell[0]['body_stable']
            evidence.append(dict(model=model['name'], protocol=protocol, directory=str(directory), trace_sha256=trace_hash))
    result = dict(passed=True, freeze_sha256=sha(args.freeze), models=len(models), cells=expected_cells,
                  independently_scored_episodes=len(trials), evidence=evidence,
                  scope='Coverage, immutable identities, conditions and unfiltered per-episode scoring verified. Capability gates are reported separately; repeated protocols share initial states.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'evidence'}))


if __name__ == '__main__':
    main()
