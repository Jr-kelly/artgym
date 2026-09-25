"""Separate endpoint and holding failures in the completed CP0/1/25 comparisons."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.publish_wuji_student_replay_results import read_trial


def main():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for scope in ['head', 'actor']:
        for cp in [0, 1, 25]:
            for seconds in [2, 5]:
                name = 'student-actionimit-%s-seed68-v5-cp%d-mixed332-timed%dseconds' % (scope, cp, seconds)
                folder, report, trace = read_trial(name)
                steps = report['protocol']['stage_steps']
                stages = []
                levels = np.unique(trace['goal'])
                # Different initial rows can differ by a few float32 ULPs.
                # Classify direction only; retain exact goals in all errors.
                midpoint = (float(levels.min()) + float(levels.max())) / 2
                assert float(levels.max() - levels.min()) > .03
                alive_all = np.array([x['alive_full'] for x in report['records']])
                assert alive_all.any()
                for start in range(0, 600, steps):
                    tail = slice(start + steps - 9, start + steps)
                    goal = trace['goal'][start]
                    opening = goal > midpoint
                    # Inactive failed episodes may retain a previous goal.
                    # All endpoint statistics below condition on survivors.
                    command = opening[alive_all][0]
                    assert (opening[alive_all] == command).all()
                    stages.append(dict(opening=bool(command),
                        signed=(trace['slider'][tail] - trace['goal'][tail]) * 1000))
                groups = []
                for lo in [0, 100, 200, 300]:
                    selected = slice(lo, lo + 100)
                    records = report['records'][selected]
                    alive = np.array([x['alive_full'] for x in records])
                    body = ((trace['drift'][:, selected] < .01) &
                            (trace['rotation'][:, selected] < .25)).all(0) & alive
                    group = dict(count=len(records), alive=int(alive.sum()), body=int(body.sum()),
                        joint=sum(x['stable_full_all_endpoints'] for x in records), endpoints={})
                    for opening in [True, False]:
                        values = np.stack([s['signed'][:, selected][:, alive] for s in stages if s['opening'] == opening])
                        assert np.isfinite(values).all()
                        error = np.abs(values)
                        # Require every sampled tail value, not just its mean.
                        worst = error.max(axis=(0, 1)) if alive.any() else np.array([])
                        group['endpoints']['open' if opening else 'close'] = dict(
                            mean_signed_mm=float(values.mean()) if values.size else None,
                            mean_absolute_mm=float(error.mean()) if error.size else None,
                            worst_tail_per_episode_median_mm=float(np.median(worst)) if worst.size else None,
                            worst_tail_per_episode_p95_mm=float(np.quantile(worst, .95)) if worst.size else None,
                            survivors_all_tails_under2mm=int((worst < 2).sum()))
                    groups.append(group)
                rows.append(dict(name=name, scope=scope, cp=cp, seconds=seconds, groups=groups,
                    trace_sha256=hashlib.sha256((folder / 'trace.npz').read_bytes()).hexdigest()))
    output = root / 'runs/wuji-goal/diagnostics/actionimit-through-cp25-endpoints-1835.json'
    output.write_text(json.dumps(dict(records=rows, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Reused development states. Endpoint distributions condition on full-rollout survivors; body and joint failures also retained. Open is larger raw joint goal. Means alone are not the all-command success criterion. No unique causal claim.'), indent=2) + '\n')
    print(json.dumps([x for x in rows if x['cp'] == 25]))


if __name__ == '__main__':
    main()
