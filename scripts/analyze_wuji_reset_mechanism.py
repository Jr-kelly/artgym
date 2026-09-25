"""Summarize all frozen normalizer and holding interventions from audited rows."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.analyze_wuji_reset_range_pair import paired


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    audit = json.loads(args.audit.read_text())
    assert audit['status'] == 'verified_complete' and audit['completed'] == audit['expected'] == 22
    assert audit['physics_transitions'] == 3198000
    args.output.mkdir(exist_ok=False)
    result = dict(status='complete_frozen_mechanism_analysis', audit_sha256=hashlib.sha256(args.audit.read_bytes()).hexdigest(),
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), conditions={}, comparisons={},
                  scope='One H100 GPU2, batch332, evaluation seed20261127, observed wider development cohort. '
                        'Normalizer swaps and fixed targets are counterfactual controllers, not newly trained policies. '
                        'No independent or hardware validation; descriptive unadjusted paired intervals.')
    for name, row in audit['results'].items():
        if not row['formal']:
            continue
        groups = row['groups']
        result['conditions'][name] = dict(success=sum(g['success'] for g in groups[:3]),
            body=sum(g['body'] for g in groups[:3]), denominator=300, groups=groups,
            trace_sha256=row['trace_sha256'], checkpoint_sha256=row['checkpoint_sha256'])
    for seconds in [2, 5]:
        comparisons = [('original', 'cp25'), ('original', 'cp50'), ('original', 'cp100'),
                       ('cp50', 'cp50-originalnorm'), ('cp100', 'cp100-originalnorm'),
                       ('original', 'original-cp100norm'), ('original', 'hold')]
        for first, second in comparisons:
            a, b = [audit['results'][f'formal-{x}-{seconds}s'] for x in [first, second]]
            result['comparisons'][f'{seconds}s:{first}->{second}'] = dict(
                success=paired([r['stable_full_all_endpoints'] for r in a['records'][:300]],
                               [r['stable_full_all_endpoints'] for r in b['records'][:300]]),
                body=paired(a['body'][:300], b['body'][:300]))
    (args.output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    (args.output/'source.py').write_bytes(Path(__file__).read_bytes())
    with (args.output/'counts.csv').open('w') as f:
        w = csv.writer(f)
        w.writerow(['condition', 'success_300', 'body_stable_300', 'a', 'b', 'c', 'fourth_32'])
        for name, value in result['conditions'].items():
            w.writerow([name, value['success'], value['body'], *[g['success'] for g in value['groups']]])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = [('original', 'Original teacher'), ('cp25', 'Continued CP25'), ('cp50', 'Continued CP50'),
              ('cp100', 'Continued CP100'), ('cp50-originalnorm', 'CP50 + original statistics'),
              ('cp100-originalnorm', 'CP100 + original statistics'),
              ('original-cp100norm', 'Original + CP100 statistics'), ('hold', 'Constant initial targets')]
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharey=True, layout='constrained')
    y = np.arange(len(labels))
    for ax, seconds in zip(axes, [2, 5]):
        values = [result['conditions'][f'formal-{key}-{seconds}s'] for key, _ in labels]
        for offset, key, color in [(-.18, 'success', 'tab:blue'), (.18, 'body', 'tab:orange')]:
            counts = [v[key] for v in values]
            bars = ax.barh(y+offset, np.array(counts)/3, height=.33, label='Complete task' if key == 'success' else 'Stable body only', color=color)
            ax.bar_label(bars, labels=[f'{n}/300' for n in counts], padding=3, fontsize=8)
        ax.set_xlim(0, 112)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_yticks(y, [label for _, label in labels])
        ax.set_xlabel('Trials (%)')
        ax.set_title(f'{seconds}s external commands')
        ax.grid(axis='x', alpha=.2)
    axes[0].invert_yaxis()
    axes[1].legend(loc='upper center', bbox_to_anchor=(.5, -.12), ncol=2, fontsize=8)
    fig.suptitle('Frozen mechanism diagnosis: all 22 stages verified\nObserved wider resets; swaps/holding are diagnostic controllers; fourth grasp 0/32 throughout')
    for ext in ['png', 'pdf']:
        fig.savefig(args.output/('mechanism-comparison.'+ext), dpi=180)
    plt.close(fig)
    print(json.dumps({k: [v['success'], v['body']] for k, v in result['conditions'].items()}))


if __name__ == '__main__':
    main()
