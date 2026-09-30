"""Independent training-state handover checks before any aggregate fitting."""
import argparse
import json
from pathlib import Path

import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.summarize_wuji_multigrasp_trace import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows, checks = [], []
    for seconds in [2, 5]:
        for source in range(4):
            pair = {}
            for mode in ['behavior', 'handover']:
                path = args.collection / f'{mode}-t{seconds}/source{source}'
                with np.load(path / 'trace.npz') as z:
                    trace = {k: z[k] for k in z.files}
                score = score_timed_trace(trace, seconds * 30, 9, 600)
                independent = summarize(trace, seconds * 30)
                assert [r['strict'] for r in independent] == [r['stable_full_all_endpoints'] for r in score['records']]
                info = json.loads((path / 'interface.json').read_text())
                assert info['teacher_replay_max_mu_error'] < 1e-5
                valid = trace['active'] & ~trace['fall'] & ~trace['invalid']
                body = valid.all(0) & (trace['drift'] < .01).all(0) & (trace['rotation'] < .25).all(0)
                row = dict(seconds=seconds, source=source, mode=mode, n=32,
                    strict=sum(r['strict'] for r in independent) / 32,
                    phase_hold=float(np.mean([r['endpoints_held'] for r in score['records']])),
                    body=float(body.mean()), all_active_initially=bool(trace['active'][0].all()))
                pair[mode] = row
                rows.append(row)
            b, h = pair['behavior'], pair['handover']
            checks.append(dict(seconds=seconds, source=source, kind='body_retention',
                passed=h['body'] >= .9 and h['body'] >= b['body'] - .05))
            if source < 3:
                checks.append(dict(seconds=seconds, source=source, kind='old_source_strict_retention',
                    passed=h['strict'] >= b['strict'] - .1))
            if source == 3 and seconds == 5:
                checks.append(dict(seconds=seconds, source=source, kind='long_open_recovery',
                    passed=h['phase_hold'] >= b['phase_hold'] + .1 or h['strict'] >= b['strict'] + .15))
    result = dict(rows=rows, checks=checks, training_allowed=all(x['passed'] for x in checks) and all(r['all_active_initially'] for r in rows),
        scope='Training-state scripted early handover, not unified success or an unconditional expert oracle. Engineering availability gate; not statistical significance.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
