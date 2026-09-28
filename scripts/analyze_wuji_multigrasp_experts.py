"""Rescore final single-source experts; these are fit diagnostics, not novel grasps."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.summarize_wuji_multigrasp_trace import summarize
from scripts.wuji_arrival_metrics import score_arrival_trace
from scripts.wuji_timed_command_metrics import score_timed_trace

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summaries, trials, temporal, inputs = [], [], [], []
    for path in args.results:
        run = json.loads(path.read_text())
        assert run['status'] == 'completed'
        plan = run['plan']
        assert sha(path.parent / 'states.npy') == plan['states_sha256']
        assert sha(ROOT / plan['checkpoint']) == plan['checkpoint_sha256']
        source = plan['source_row']
        inputs.append(dict(path=str(path), sha256=sha(path), plan=plan))
        static = None
        assert [r['protocol'] for r in run['results']] == ['static', 'fixed2', 'fixed5', 'arrival']
        for result in run['results']:
            evidence = ROOT / result['evidence']
            saved, protocol = result['report'], result['protocol']
            assert saved['initial_states_sha256'] == plan['states_sha256']
            assert saved['checkpoint_sha256'] == plan['checkpoint_sha256']
            with np.load(evidence / 'trace.npz') as archive:
                trace = {key: archive[key] for key in archive.files}
            assert trace['active'].shape == (600, 32)
            alive = (trace['active'] & ~trace['fall'] & ~trace['invalid']).all(0)
            stable = alive & (trace['drift'] < .01).all(0) & (trace['rotation'] < .25).all(0)
            if protocol == 'static':
                assert saved['alive_full'] == int(alive.sum()) and saved['recorded_steps'] == 600
                static = dict(alive=alive, stable=stable)
                summaries.append(dict(source_row=source, protocol=protocol, n=32,
                                      successes=None, alive_full=int(alive.sum()),
                                      static_stable=int(stable.sum())))
                continue
            if protocol == 'arrival':
                rescored = score_arrival_trace(trace, 600, .01)
                metric = 'three_cycles'
            else:
                steps = 150 if protocol == 'fixed5' else 60
                rescored = score_timed_trace(trace, steps, 9, 600)
                metric = 'stable_full_all_endpoints'
                details = summarize(trace, steps)
                for i, detail in enumerate(details):
                    assert detail['strict'] == rescored['records'][i][metric]
                    temporal.append(dict(source_row=source, protocol=protocol, **detail))
            for key, value in rescored.items():
                assert saved[key] == value, (source, protocol, key)
            rows = []
            for i, record in enumerate(rescored['records']):
                rows.append(dict(source_row=source, protocol=protocol, trial=i,
                                 success=bool(record[metric]), alive_full=record['alive_full'],
                                 static_alive=bool(static['alive'][i]), static_stable=bool(static['stable'][i]),
                                 cycles=record['cycles'] if protocol == 'arrival' else
                                 sum(all(record['endpoints_held'][j:j+2]) for j in range(0, len(record['endpoints_held']), 2)),
                                 max_drift_mm=record['max_drift_m'] * 1000,
                                 max_rotation_deg=float(np.rad2deg(record['max_rotation_rad']))))
            trials.extend(rows)
            summaries.append(dict(source_row=source, protocol=protocol, n=32,
                                  successes=sum(r['success'] for r in rows),
                                  alive_full=sum(r['alive_full'] for r in rows),
                                  static_stable=int(static['stable'].sum()),
                                  success_on_static_stable=sum(r['success'] and r['static_stable'] for r in rows),
                                  trace_sha256=sha(evidence / 'trace.npz')))
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'trials.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(trials[0]))
        writer.writeheader()
        writer.writerows(trials)
    (args.output / 'temporal-diagnostics.json').write_text(json.dumps(temporal, indent=2) + '\n')
    report = dict(status='independently_rescored', inputs=inputs, summaries=summaries,
                  physical_policy_trials=len(trials), training_seed=2026092810,
                  scope='Three single-training-source experts, final1000 only, 32 independently generated perturbations each. Not unseen-grasp generalization or a matrix seed replication. Failure does not prove physical impossibility.')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
