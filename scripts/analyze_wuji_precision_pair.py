"""Compare paired perturbations and failure stages without rerunning physics."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root/'runs/wuji-goal/verification'
    names = ['precision-teacher-cp10-perturb-small', 'precision-near01-cp50-perturb-small',
             'precision-near1-cp50-perturb-small']
    data = {}; initial = None
    for name in names:
        folder = base/name
        report = json.loads((folder/'report.json').read_text())
        states = np.load(folder/'perturbed_initial_states.npy')
        if initial is None:
            initial = states
        else:
            np.testing.assert_array_equal(initial, states)
        trace = np.load(folder/'trace.npz')
        categories = Counter(); reasons = Counter(); outcomes = []
        for i, row in enumerate(report['records']):
            mask = trace['active'][:, i]
            events = np.flatnonzero(trace['stage_event'][:, i]*mask)
            if row['cycles'] >= 1:
                category = 'complete_cycle'
            elif len(events) >= 1:
                category = 'opened_not_closed'
            else:
                # The fixed precision knife starts at zero; first target is40mm.
                near = np.abs(trace['slider'][mask, i]-.04) < .002
                category = 'entered_open_tolerance_without_dwell' if near.any() else 'never_entered_open_tolerance'
            categories[category] += 1
            reasons[row['completion_reason']] += 1
            full_drift = float(trace['drift'][mask, i].max())
            full_rotation = float(trace['rotation'][mask, i].max())
            outcomes.append(dict(complete=row['cycles'] >= 1,
                strict=row['cycles'] >= 1 and row['first_cycle_max_drift_m'] < .01 and row['first_cycle_max_rotation_rad'] < .25,
                full=row['cycles'] >= 1 and full_drift < .01 and full_rotation < .25 and
                     row['completion_reason'] == 'episode_timeout' and not row['fall'] and not row['invalid']))
        data[name] = dict(report_sha256=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),
            initial_states_sha256=hashlib.sha256((folder/'perturbed_initial_states.npy').read_bytes()).hexdigest(),
            checkpoint_sha256=report['checkpoint_sha256'], categories=dict(categories),
            completion_reasons=dict(reasons), metrics={key:sum(row[key] for row in outcomes) for key in ['complete', 'strict', 'full']},
            outcomes=outcomes)
    paired = {}
    for control in [names[0], names[2]]:
        paired[control] = {}
        for metric in ['complete', 'strict', 'full']:
            a = [r[metric] for r in data[names[1]]['outcomes']]
            b = [r[metric] for r in data[control]['outcomes']]
            paired[control][metric] = dict(both=sum(x and y for x,y in zip(a,b)),
                near01_only=sum(x and not y for x,y in zip(a,b)),
                comparator_only=sum(y and not x for x,y in zip(a,b)),
                neither=sum(not x and not y for x,y in zip(a,b)))
    out = dict(initial_states_exactly_equal=True, trials=100, seed=1616,
               scope='One training seed per matched arm; one nominal grasp with100independent prescribed perturbations. Development comparison, not unseen-geometry/hardware validation. Audit reward sums are not directly comparable to training reward when its coefficient differs.',
               runs=data, paired_near01_vs=paired)
    target = root/'runs/wuji-goal/diagnostics/precision-near-reward-cp50-paired.json'
    target.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({k:{'metrics':v['metrics'], 'categories':v['categories']} for k,v in data.items()}, indent=2))


if __name__ == '__main__':
    main()
