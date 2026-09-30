"""Score remaining restored final traces and merge the cached primary verification."""
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.record_wuji_recovery import R, D, record


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # System ssh must not load the scientific Conda runtime's different OpenSSL.
    orchestration_env = os.environ.copy()
    orchestration_env.pop('LD_LIBRARY_PATH', None)
    subprocess.run(['/usr/bin/python3', '-m', 'scripts.status_wuji_recovery', '--pull'],
                   cwd=R, env=orchestration_env, stdout=subprocess.DEVNULL, check=True)
    jobs = json.loads((D / 'resources/latest.json').read_text())['jobs']
    assert all(any(j['name'] == name and j['status'] == 'completed' for j in jobs)
               for name in ['final-g0-job', 'final-g1-job'])
    frozen = json.loads((D / 'final-freeze.json').read_text())
    primary = D / 'final-primary-analysis'
    provenance = json.loads((primary / 'provenance.json').read_text())
    assert provenance['freeze_sha256'] == sha(D / 'final-freeze.json')
    assert provenance['scorer_source_sha256'] == sha(R / 'scripts/summarize_wuji_recovery.py')
    assert provenance['models'] == [frozen['overall_candidate']]
    remaining, output = D / 'final-remaining-analysis', D / 'final-analysis'
    assert not remaining.exists() and not output.exists(), 'Audit partial prior analysis before retry'
    record('remaining_final_independent_rescore_started',
           cached_primary=str(primary.relative_to(R)),
           next='Read restored remaining17 models only; reuse independently verified primary without repeating simulation or scoring')
    restored = Path('/tmp/wuji-recovery-final-restore/runs/artmanip-recovery-20260930')
    with tempfile.TemporaryDirectory(prefix='wuji-final-remaining-views-') as temporary:
        views = []
        for batch in ['final-g0', 'final-g1']:
            original = R / 'runs/artmanip-recovery-20260930' / batch
            assert (original / 'completed.json').exists() and (restored / batch / 'completed.json').exists()
            assert sha(original / 'results.json') == sha(restored / batch / 'results.json')
            rows = [x for x in json.loads((restored / batch / 'results.json').read_text())
                    if x['model'] != frozen['overall_candidate']]
            view = Path(temporary) / batch
            view.mkdir()
            (view / 'results.json').write_text(json.dumps(rows) + '\n')
            for row in rows:
                (view / row['directory']).symlink_to(restored / batch / row['directory'], target_is_directory=True)
            views.append(str(view))
        subprocess.run([sys.executable, '-m', 'scripts.summarize_wuji_recovery',
                        '--directories', *views, '--output', str(remaining)], cwd=R, check=True)
    rows, clusters, trials, inputs = [], [], [], []
    for directory in [primary, remaining]:
        report = json.loads((directory / 'report.json').read_text())
        assert report['independent_rescore'] == 'passed'
        rows += report['rows']
        clusters += json.loads((directory / 'clusters.json').read_text())
        with (directory / 'trials.csv').open() as stream:
            trials += list(csv.DictReader(stream))
        inputs.append(dict(path=str(directory.relative_to(R)), report_sha256=sha(directory / 'report.json'),
                           trials_sha256=sha(directory / 'trials.csv'), clusters_sha256=sha(directory / 'clusters.json')))
    keys = {(r['model'], r['protocol'], r['source']) for r in rows}
    expected = {(m, p, s) for m in frozen['models'] for p in frozen['protocols'] for s in range(4)}
    assert len(keys) == len(rows) and keys == expected
    assert len(trials) == len(expected) * 128
    assert len(clusters) == len(frozen['models']) * 3 * 3
    output.mkdir()
    (output / 'report.json').write_text(json.dumps(dict(rows=rows, independent_rescore='passed'), indent=2) + '\n')
    (output / 'clusters.json').write_text(json.dumps(clusters, indent=2) + '\n')
    with (output / 'trials.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trials[0]))
        writer.writeheader()
        writer.writerows(trials)
    (output / 'provenance.json').write_text(json.dumps(dict(inputs=inputs,
        freeze_sha256=sha(D / 'final-freeze.json'), independent_scorer_sha256=sha(R / 'scripts/summarize_wuji_recovery.py'),
        scope='All54 physical cells independently rescored from actually restored archives; cached primary plus remaining17 models. No new rollouts or threshold changes.'), indent=2) + '\n')
    record('all_final_independent_scores_merged', models=len(frozen['models']), source_cells=len(rows),
           episodes=len(trials), evidence=str(output.relative_to(R)),
           next='Run final completeness audit and exact same-cohort expert gates; report all fixed endpoints')


if __name__ == '__main__':
    main()
