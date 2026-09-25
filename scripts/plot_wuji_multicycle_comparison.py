"""Publish the matched reset-condition experiment, including unmet quality gates."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    sources = ['multicycle-cp100-all5-trace160', 'multicycle_control-cp100-all5-trace160']
    reports = [json.loads((root/'runs/wuji-goal/verification'/s/'report.json').read_text()) for s in sources]
    assert all(r['envs'] == 160 and r['base_grasps'] == 5 and r['seed'] == 2121 for r in reports)
    out = root/'runs/wuji-goal/release-multicycle-pair-20260922-0300'
    out.mkdir(parents=True, exist_ok=True)
    prefix = 'wuji-knife-multicycle-reset-comparison-cp100-20260922'
    keys = ['successful_trials', 'strict_first_cycle_trials', 'stable_full_rollout_trials']
    names = ['Train continuous cycles', 'Reset after one cycle']
    colors = ['#287aa9', '#cb813b']
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={'width_ratios': [1.25, 1]})
    for j, (report, name, color) in enumerate(zip(reports, names, colors)):
        x = np.arange(3) + (j-.5)*.34
        counts = np.array([report[k] for k in keys])
        bars = axes[0].bar(x, counts/160*100, .32, label=name, color=color)
        for bar, count in zip(bars, counts):
            axes[0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+2, '%s/160' % count, ha='center', fontsize=9)
        strict = []
        for i in range(5):
            rows = [r for r in report['records'] if r['grasp_index'] == i]
            assert len(rows) == 32
            strict.append(sum(r['cycles'] >= 1 and r['first_cycle_max_drift_m'] < .01 and
                              r['first_cycle_max_rotation_rad'] < .25 for r in rows))
        assert sum(strict) == report['strict_first_cycle_trials']
        bars = axes[1].bar(np.arange(5)+(j-.5)*.34, np.array(strict)/32*100, .32, color=color)
        for bar, count in zip(bars, strict):
            axes[1].text(bar.get_x()+bar.get_width()/2, bar.get_height()+2, str(count), ha='center', fontsize=9)
    axes[0].set_xticks(np.arange(3), ['At least one\nfull cycle', 'Stable\nfirst cycle', 'Stable\nfull rollout'])
    axes[0].set_title('Same source policy, seed and 100 training updates')
    axes[0].set_ylabel('Trials meeting criterion (%)')
    axes[0].legend(loc='upper right', fontsize=9)
    axes[1].set_xticks(np.arange(5), [str(i) for i in range(5)])
    axes[1].set_title('Stable first cycles per held-out grasp')
    axes[1].set_xlabel('Grasp index (labels above bars: count out of 32)')
    for ax in axes:
        ax.set_ylim(0, 119)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle('Wuji knife: later-cycle training helps, but sustained pose stability remains unsolved', fontsize=12)
    fig.text(.02, .015, '5 held-out grasps of one geometry x 32 repetitions; 5 mm goal tolerance, no dwell; 20 s rollout.\n'
             'Stable pose: base displacement <10 mm and rotation <0.25 rad. Repetitions are not new grasps or hardware trials.', fontsize=9)
    fig.tight_layout(rect=[0, .1, 1, .94])
    fig.savefig(out/(prefix+'.png'), dpi=160)
    plt.close(fig)
    provenance = dict(source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      intervention='Only maxConsecutiveSuccesses=0 versus2 in training')
    # Read the full immutable source hash from the registered paired run.
    manifest = json.loads((root/'wuji_acquisition_suite.json').read_text())
    provenance['source_checkpoint_sha256'] = manifest['experiments']['wuji_acq_multicycle_v1']['initial_checkpoint_sha256']
    provenance['reports'] = [dict(path='runs/wuji-goal/verification/'+s+'/report.json',
        sha256=hashlib.sha256((root/'runs/wuji-goal/verification'/s/'report.json').read_bytes()).hexdigest(),
        checkpoint_sha256=r['checkpoint_sha256'], counts={key:r[key] for key in keys}) for s,r in zip(sources,reports)]
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance, indent=2)+chr(10))
    notes = '''# Wuji continuous-cycle training comparison

Both arms start from the same multigrasp CP100 model and normalization, with fresh optimizers,
seed 20260930, 5120 environments, horizon 32 and LR 5e-5. Only the training reset condition differs:
continuous cycles up to 20 seconds versus reset after one complete cycle. Results below use
100 additional updates in each arm, five validation grasps of the same geometry, 32 repetitions
each, deterministic block 0, seed 2121. All training and validation rows are retained.

| Arm | Complete open-close | Stable first cycle | Stable full 20 seconds |
| --- | ---: | ---: | ---: |
| Continuous-cycle training | 128/160 | 59/160 | 0/160 |
| Reset after one cycle | 90/160 | 32/160 | 0/160 |

Pose limits remain strictly below 10 mm translation and 0.25 rad rotation relative to the
initial object pose. A full-rollout pass also requires a complete cycle, reaching episode
timeout without a fall or invalid state. Goal tolerance is 5 mm, with no dwell requirement.
This experiment does not use the separate precision task's 2 mm / 0.3-second criteria.

Continuous-cycle training improves first-cycle results in this matched-seed comparison,
but neither arm passes sustained pose stability. Grasp 2 fails in both arms. Repeated
rollouts are not independent new grasps, unseen geometries, or hardware trials. Further
training seeds and fresh held-out testing are needed for a general causal claim.

The plot, raw-count provenance, and SHA256SUMS preserve the zero results. This is a
diagnostic result, not a final successful demonstration or hardware deployment validation.
'''
    (out/(prefix+'-results.md')).write_text(notes)
    checks = [(file.name, hashlib.sha256(file.read_bytes()).hexdigest()) for file in sorted(out.iterdir())
              if not file.name.endswith('SHA256SUMS.txt')]
    (out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(digest+'  '+name+'\n' for name,digest in checks))
    print(out)


if __name__ == '__main__':
    main()
