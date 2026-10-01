"""Describe development failure trajectories without treating stages as samples."""
import csv
import json
import re
import statistics
from pathlib import Path


def main():
    root = Path('research/unified-student-20261001')
    output = []
    for path in sorted(root.glob('*-development-analysis/trials.csv')):
        model = path.parent.name[:-len('-development-analysis')]
        match = re.fullmatch(r'(S0|SA-real|SC-real|SC-masked|C1)-(\d+)', model)
        if not match:
            continue
        with path.open() as stream:
            trials = [r for r in csv.DictReader(stream) if r['model'] == model]
        for protocol in ['S2', 'S5']:
            period = int(protocol[1:])
            for source in range(4):
                rows = [r for r in trials if r['protocol'] == protocol and int(r['source']) == source]
                if not rows:
                    continue
                assert len(rows) == 32 and len({r['trial'] for r in rows}) == 32
                assert len({r['cohort_sha256'] for r in rows}) == 1
                stable = [r for r in rows if r['body_stable'] == 'True']
                stable_misses = [r for r in stable if '0' in r['endpoint_holds']]
                strict = sum(r['success'] == 'True' for r in rows)
                assert strict == sum('0' not in r['endpoint_holds'] for r in stable)
                before_breach = 0
                first_misses = []
                for row in rows:
                    holds = row['endpoint_holds']
                    assert len(holds) == 20 // period
                    if '0' in holds:
                        end = (holds.index('0') + 1) * period
                        first_misses.append(end)
                        before_breach += end <= float(row['first_body_breach_sec'])
                breaches = [float(r['first_body_breach_sec']) for r in rows if r['body_stable'] != 'True']
                output.append(dict(model=model, method=match[1], update=int(match[2]),
                    protocol=protocol, source=source, n=32, strict_success=strict,
                    body_stable=len(stable), stable_but_endpoint_failed=len(stable_misses),
                    body_failed=len(breaches),
                    stable_opening_failed=sum('0' in r['endpoint_holds'][::2] for r in stable),
                    stable_closing_failed=sum('0' in r['endpoint_holds'][1::2] for r in stable),
                    first_failed_endpoint_before_body_breach=before_breach,
                    first_failed_endpoint_median_sec=statistics.median(first_misses) if first_misses else None,
                    body_breach_median_among_failed_sec=statistics.median(breaches) if breaches else None,
                    cohort_sha256=rows[0]['cohort_sha256'], evidence=str(path)))
    output.sort(key=lambda r: (r['method'], r['update'], r['protocol'], r['source']))
    report = dict(scope='Development-only episode counts from independently rescored traces. '
        'Strict failures partition into full-horizon body-stable endpoint misses and body failures. '
        'Opening/closing failures may overlap. Timing is descriptive, not causal; '
        'checkpoints reuse initial states and do not enlarge sample denominators.', rows=output)
    (root / 'development-failure-decomposition.json').write_text(json.dumps(report, indent=2) + '\n')
    with (root / 'development-failure-decomposition.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print(json.dumps(dict(cells=len(output), models=len({r['model'] for r in output}))))


if __name__ == '__main__':
    main()
