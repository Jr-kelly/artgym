"""Describe fixed reset-range development trajectories without selecting a policy."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import yaml


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired(first, second):
    """Paired, grasp-stratified bootstrap; descriptive, no multiple-test correction."""
    difference = np.asarray(second, dtype=np.int8)-np.asarray(first, dtype=np.int8)
    assert difference.shape == (300,)
    rng = np.random.default_rng(20261126)
    draws = np.zeros(10000)
    for start in [0, 100, 200]:
        indices = rng.integers(start, start+100, size=(10000, 100))
        draws += difference[indices].sum(axis=1)/300
    return dict(delta_success=int(difference.sum()),
                repaired=int((difference == 1).sum()), regressed=int((difference == -1).sum()),
                bootstrap95_fraction=np.quantile(draws, [.025, .975]).tolist(),
                caveat='Observed development rows; descriptive unadjusted interval, single training seed.')


def describe(trace, states, report):
    valid = trace['active'] & ~trace['fall'] & ~trace['invalid']
    pose = np.isfinite(trace['drift']) & np.isfinite(trace['rotation'])
    pose &= (trace['drift'] < .01) & (trace['rotation'] < .25)
    body_step = valid & pose
    body = body_step.all(axis=0)
    success = np.array([r['stable_full_all_endpoints'] for r in report['records']])
    assert np.all(~success | body)
    # The first sample is after one physical control transition, not time zero.
    first = np.where(body, 600, np.argmax(~body_step, axis=0))
    before_failure = np.arange(600)[:, None] < first[None, :]
    before_failure &= valid
    span = report['action_control']['support_span_rad']
    assert span == .04
    support_fraction = np.abs(trace['target'][:, :, :16]-states[None, :, 20:36])/span
    tracking = np.abs(trace['target']-trace['q'])
    groups = []
    for start, stop in [(0, 100), (100, 200), (200, 300), (300, 332)]:
        ids = np.arange(start, stop)
        failed = ids[~body[ids]]
        times = (first[failed]+1)/30
        stats = {}
        for label, selected in [('joint_success', ids[success[ids]]), ('body_failure', failed),
                                ('body_stable_endpoint_failure', ids[body[ids] & ~success[ids]])]:
            mask = before_failure[:, selected]
            values = support_fraction[:, selected][mask]
            target_error = tracking[:, selected][mask]
            actions = trace['action'][:, selected][mask]
            stats[label] = dict(trials=int(len(selected)), control_transitions=int(mask.sum()))
            if mask.any():
                stats[label].update(
                    any_support_target_near_limit_fraction=float((values >= .95).any(axis=1).mean()),
                    support_target_near_limit_joint_fractions=(values >= .95).mean(axis=0).tolist(),
                    support_action_near_limit_fraction=float((np.abs(actions[:, :16]) >= .95).mean()),
                    thumb_action_near_limit_fraction=float((np.abs(actions[:, 16:]) >= .95).mean()),
                    support_tracking_rad_q50_q95=np.quantile(target_error[:, :16], [.5, .95]).tolist(),
                    thumb_tracking_rad_q50_q95=np.quantile(target_error[:, 16:], [.5, .95]).tolist())
        endpoint_errors = []
        step = report['protocol']['stage_steps']
        for begin in range(0, 600, step):
            selected = ids[body[ids]]
            errors = np.abs(trace['slider'][begin+step-9:begin+step, selected]
                            - trace['goal'][begin+step-9:begin+step, selected])
            endpoint_errors.append(dict(stage=begin//step, opening=(begin//step) % 2 == 0,
                                        body_stable_trials=len(selected),
                                        max_9frame_error_m_q50_q95=(np.quantile(errors.max(axis=0), [.5, .95]).tolist()
                                                                    if len(selected) else None)))
        groups.append(dict(count=stop-start, success=int(success[ids].sum()), body=int(body[ids].sum()),
                           body_failure_by_time=dict(first_half_second=int((times <= .5).sum()),
                                                     half_to_two_seconds=int(((times > .5) & (times <= 2)).sum()),
                                                     after_two_seconds=int((times > 2).sum())),
                           body_failure_times_seconds=times.tolist(),
                           pre_failure_controls=stats, stable_body_endpoints=endpoint_errors))
    return dict(success=success.tolist(), body=body.tolist(), groups=groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--arms', nargs=2, default=['reset1x', 'reset2x'])
    parser.add_argument('--title', default='Reset-range continuation')
    parser.add_argument('--remote-root', type=Path)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    assert audit['status'] in ['verified_partial', 'verified_complete']
    assert audit['expected'] == 44
    baseline = [name for name in audit['results'] if re.fullmatch(r'.+-frozen-cp25-small-2s-(?:local|h100)-v\d+', name)]
    assert len(baseline) == 1
    prefix, suffix_version = baseline[0].split('frozen-cp25-small-2s')
    args.output.mkdir(exist_ok=False)
    conditions = {}
    physical_config = None
    for name, audited in audit['results'].items():
        folder = args.root/'runs/wuji-goal/verification'/name
        assert sha(folder/'trace.npz') == audited['trace_sha256']
        report = json.loads((folder/'report.json').read_text())
        cfg = yaml.safe_load((folder/'config.yaml').read_text())
        current = {k: cfg[k] for k in ['task', 'object', 'hand']}
        if physical_config is None:
            physical_config = current
        assert physical_config == current, name
        initial = Path(audited['initial_states'])
        if initial.is_absolute() and args.remote_root:
            initial = args.root/initial.relative_to(args.remote_root)
        else:
            initial = args.root/initial
        assert sha(initial) == audited['initial_states_sha256']
        with np.load(folder/'trace.npz') as z:
            trace = {k: z[k] for k in z.files}
        result = describe(trace, np.load(initial), report)
        assert sum(result['success'][:300]) == audited['success']
        assert sum(result['body'][:300]) == audited['body']
        conditions[name] = dict(**result, checkpoint_sha256=audited['checkpoint_sha256'],
                                trace_sha256=audited['trace_sha256'])
    comparisons = {}
    for cohort in ['small', 'wider']:
        for seconds in [2, 5]:
            suffix = f'-{cohort}-{seconds}s'+suffix_version
            base = prefix+'frozen-cp25'+suffix
            for cp in [10, 25, 50, 75, 100]:
                one = prefix+f'{args.arms[0]}-cp{cp}'+suffix
                two = prefix+f'{args.arms[1]}-cp{cp}'+suffix
                for first, second in [(base, one), (base, two), (one, two)]:
                    if first in conditions and second in conditions:
                        comparisons[first+'__TO__'+second] = dict(
                            success=paired(conditions[first]['success'][:300], conditions[second]['success'][:300]),
                            body=paired(conditions[first]['body'][:300], conditions[second]['body'][:300]))
    result = dict(status=audit['status'], completed=len(conditions), expected=44,
                  audit=str(args.audit), audit_sha256=sha(args.audit), source_sha256=sha(Path(__file__)),
                  conditions=conditions, comparisons=comparisons,
                  scope='All available prespecified CPs. Previously observed development cohorts, batch332. '
                        'Controls are descriptive before first body failure; saturation correlation is not causation. '
                        'Fourth32 retained. No checkpoint selected, no independent/hardware claim.')
    (args.output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    with (args.output/'counts.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['condition', 'success_300', 'body_stable_300', 'a', 'b', 'c', 'fourth_32'])
        for name, condition in conditions.items():
            counts = [g['success'] for g in condition['groups']]
            writer.writerow([name, sum(counts[:3]), sum(condition['body'][:300]), *counts])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout='constrained')
    for row, cohort in enumerate(['small', 'wider']):
        for col, seconds in enumerate([2, 5]):
            ax = axes[row, col]
            suffix = f'-{cohort}-{seconds}s'+suffix_version
            base = conditions[prefix+'frozen-cp25'+suffix]
            minimum = sum(base['success'][:300])/3
            ax.axhline(sum(base['success'][:300])/3, color='black', label='Frozen teacher', linestyle=':')
            for arm, color in zip(args.arms, ['tab:blue', 'tab:orange']):
                points = [(cp, conditions[prefix+f'{arm}-cp{cp}'+suffix])
                          for cp in [10, 25, 50, 75, 100]
                          if prefix+f'{arm}-cp{cp}'+suffix in conditions]
                ax.plot([p[0] for p in points], [sum(p[1]['success'][:300])/3 for p in points],
                        'o-', color=color, label=arm+' success')
                minimum = min([minimum]+[sum(p[1]['success'][:300])/3 for p in points])
                ax.plot([p[0] for p in points], [sum(p[1]['body'][:300])/3 for p in points],
                        '--', color=color, alpha=.6, label=arm+' body stable')
            ax.axhline(95, color='gray', linestyle='-.', linewidth=.8, label='95% working target')
            ax.set(title=f'{cohort} development resets, {seconds}s commands', ylim=(max(0, min(65, minimum-5)), 101),
                   xlim=(0, 105), xlabel='Additional training epochs', ylabel='Trials (%)')
            ax.grid(alpha=.2)
    axes[1, 0].legend(fontsize=7, ncol=2, loc='lower left')
    fig.suptitle(f'{args.title}: {len(conditions)}/44 completed conditions\n'
                 'Same three training grasps; observed development data; no independent test')
    for extension in ['png', 'pdf']:
        fig.savefig(args.output/('checkpoint-curves.'+extension), dpi=180)
    plt.close(fig)
    print(json.dumps(dict(status=result['status'], completed=result['completed'], output=str(args.output))))


if __name__ == '__main__':
    main()
