"""Tabulate independently rescored replications and every integration source."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research/hold-20260929'
PROTOCOLS = ['fixed2', 'fixed5']


def read(name):
    report = json.loads((RESEARCH / name / 'report.json').read_text())
    assert report['status'] == 'independently_rescored'
    return report


def pair(report, source, model):
    return [next(row for row in report['summaries'] if
                 (row['source'], row['model'], row['protocol']) ==
                 (source, model, protocol)) for protocol in PROTOCOLS]


def mean(rows, key='success'):
    return sum(100 * row[key] / row['n'] for row in rows) / len(rows)


def main():
    reports = {seed: read('analysis-' + seed) for seed in ['seed2901', 'seed2902']}
    integration = read('analysis-integration')
    replication = []
    for seed, report in reports.items():
        original = pair(report, 3, 'original-final')
        changed = pair(report, 3, 'dense1-final')
        replication.append(dict(seed=seed, original=original, changed=changed,
                                original_mean_pct=mean(original), changed_mean_pct=mean(changed),
                                change_pp=mean(changed)-mean(original),
                                body_change_pp=mean(changed, 'body_stable')-mean(original, 'body_stable')))
    gate = []
    for source in integration['plan']['sources']:
        models = {model: pair(integration, source, model)
                  for model in ['historical', 'parent', 'singleton', 'shared']}
        gate.append(dict(source=source, models=models,
                         shared_passes_both=all(row['success']/row['n'] >= .5 for row in models['shared']),
                         shared_minus_singleton_pp=mean(models['shared'])-mean(models['singleton']),
                         shared_minus_parent_pp=mean(models['shared'])-mean(models['parent'])))
    output = RESEARCH / 'followup-summary'
    output.mkdir(exist_ok=False)
    result = dict(replication=replication, integration=gate,
                  shared_passes_every_source_protocol=all(row['shared_passes_both'] for row in gate),
                  scope='Fixed final checkpoints only. Replication changes continuation RNG, with the same parent and test cohort. Integration source3 reuses the tested cohort; originals0/1/2 represent two nearby clusters. No unseen-base or hardware claim.')
    counts_by_group = {}
    base = ROOT/'runs/hold-20260929'
    for group, pattern in [('core_final', 'final-row*-seed2901/results.json'),
                           ('replication_final', 'final-row3-seed2902/results.json'),
                           ('core_development', 'dev-hold_r*_seed2901/results.json'),
                           ('replication_development', 'dev-hold_r*_seed2902/results.json'),
                           ('integration_final', 'integration-final3000-seed2903/results.json')]:
        unique, reported = {}, 0
        for path in base.glob(pattern):
            for item in json.loads(path.read_text())['results']:
                n = item['report']['num_envs']
                reported += n
                unique[item['evidence']] = n
        assert unique, group
        counts_by_group[group] = dict(actual_physical_episodes=sum(unique.values()),
                                      reported_rows_including_explicit_reuse=reported,
                                      unique_physical_runs=len(unique))
    result['physical_evaluation_counts'] = counts_by_group
    (output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    lines = ['# Followup frozen results', '',
             '|Continuation seed|Original 2s / 5s|Changed 2s / 5s|Original mean|Changed mean|Difference|',
             '|---|---|---|---:|---:|---:|']
    counts = lambda rows: ' / '.join(f"{r['success']}/{r['n']}" for r in rows)
    for row in replication:
        lines.append(f"|{row['seed']}|{counts(row['original'])}|{counts(row['changed'])}|{row['original_mean_pct']:.2f}%|{row['changed_mean_pct']:.2f}%|{row['change_pp']:+.2f} pp|")
    lines += ['', '|Source|Historical 2s / 5s|Parent 2s / 5s|Singleton 2s / 5s|Shared 2s / 5s|Both >=50%|',
              '|---|---|---|---|---|---|']
    for row in gate:
        cells = '|'.join(counts(row['models'][model]) for model in ['historical', 'parent', 'singleton', 'shared'])
        lines.append(f"|{row['source']}|{cells}|{row['shared_passes_both']}|")
    lines += ['', result['scope'], '']
    (output/'README.md').write_text('\n'.join(lines))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharey=True)
    for ax, row in zip(axes.flat, gate):
        for j, (model, values) in enumerate(row['models'].items()):
            bars = ax.bar([x+(j-1.5)*.2 for x in range(2)],
                          [100*r['success']/r['n'] for r in values], .19, label=model)
            ax.bar_label(bars, labels=[str(r['success']) for r in values], fontsize=8, padding=2)
        ax.axhline(50, color='gray', linestyle=':', linewidth=1)
        ax.set(title=f"Source {row['source']} (128 trials / protocol)",
               xticks=[0, 1], xticklabels=['2-second commands', '5-second commands'], ylim=(0, 110))
        ax.set_ylabel('Strict 20-second success (%)')
    fig.legend(*axes.flat[0].get_legend_handles_labels(), loc='lower center', ncol=4, frameon=False)
    fig.suptitle('Frozen CP3000 shared policy: every source reported')
    fig.tight_layout(rect=[0, .04, 1, .96])
    for ext in ['png', 'pdf']:
        fig.savefig(output/('integration-by-source.'+ext), dpi=180)
    plt.close(fig)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
