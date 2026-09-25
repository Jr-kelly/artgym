"""Package completed resistance attribution and training-selected preload diagnostics."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root/'runs/wuji-goal'
    diag = base/'diagnostics'
    spring = diag/'multigrasp-spring-preload-v2-correct-geometry'
    factorial = diag/'official-timed10-resistance-factorial'
    sensitivity = diag/'official-timed10-resistance'
    completion = json.loads((spring/'offline-completion-status.json').read_text())
    assert completion['status'] == 'completed'
    for p in [factorial, sensitivity]:
        status = json.loads((p/'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
    selection = json.loads((spring/'selection.json').read_text())
    resistance = json.loads((sensitivity/'resistance_report.json').read_text())
    crossed = json.loads((factorial/'factorial_report.json').read_text())
    validation_path = root/completion['validation_report']
    validation = json.loads(validation_path.read_text())
    out = base/'release-contact-diagnostics-20260922'
    out.mkdir(parents=True, exist_ok=True)
    prefix = 'wuji-knife-resistance-contact-diagnostics-20260922'
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7), constrained_layout=True)
    x = np.arange(5)
    for offset, key, label, color in [(-.19, 'first_cycle_strict', 'Stable first cycle', '#4678b5'),
                                    (.19, 'stable_full_all_endpoints', 'Full stable + every endpoint held', '#2b9278')]:
        values = [r[key] for r in resistance['results']]
        bars = axes[0].bar(x+offset, values, width=.38, label=label, color=color)
        axes[0].bar_label(bars)
    axes[0].set(xticks=x, xticklabels=['0.3', '3', '30', '100', '300'], ylim=(0,24),
                xlabel='Actual = observed damping (N s/m)', ylabel='Trials passing / 20', title='Matched-input resistance sensitivity')
    axes[0].legend(fontsize=8, loc='upper right')
    for ax, key, title in zip(axes[1:], ['first_cycle_strict', 'stable_full_all_endpoints'],
                              ['Stable first cycle / 20', 'Full stable + every endpoint held / 20']):
        matrix = np.array([r[key] for r in crossed['results']]).reshape(3,3)
        ax.imshow(matrix, vmin=0, vmax=20, cmap='YlGnBu')
        for (i,j), value in np.ndenumerate(matrix):
            ax.text(j,i,str(value),ha='center',va='center',color='white' if value>12 else 'black',fontsize=16)
        ax.set(xticks=range(3),yticks=range(3),xticklabels=['0.3','3','30'],yticklabels=['0.3','3','30'],
               xlabel='Observed damping (N s/m)',ylabel='Actual damping (N s/m)',title=title)
    fig.suptitle('Frozen teacher CP10 | same 20 initial states per condition | 2 s commands, 20 s rollout\nOff-diagonal inputs are deliberately incorrect diagnostics; no hardware calibration', fontsize=11)
    fig.savefig(out/(prefix+'-resistance.png'),dpi=160);plt.close(fig)

    rows = selection['training_results']
    fig, ax = plt.subplots(figsize=(12,5.5),constrained_layout=True)
    labels = ['Original']+[str(r['setting']['fraction'])+'\n'+('Support only' if r['setting']['support_only'] else 'All joints') for r in rows[1:]]
    bars = ax.bar(range(len(rows)),[r['stable20s'] for r in rows],color=['#2b9278' if i==selection['selected_index'] else '#4678b5' for i in range(len(rows))])
    ax.bar_label(bars)
    ax.set(xticks=range(len(rows)),xticklabels=labels,ylim=(0,35),ylabel='20 s stable grasps / 33 training grasps',
           xlabel='Fraction of estimated old proportional spring error (not measured torque)',
           title='Official Wuji gains: initial target preload probe, correct fingertip object frame')
    stable = sum(r['stable20s'] for r in validation['records'])
    falls = sum(r['fall'] for r in validation['records'])
    ax.text(.02,.97,f'Train-only selected setting: 0.05, all joints | Held-out: {stable}/5 stable, {falls}/5 falls\nStatic holding only; no slider actuation. Original target-guard failure retained; separate float32 audit passed.',
            transform=ax.transAxes,va='top',fontsize=10,bbox=dict(facecolor='white',edgecolor='#cccccc'))
    fig.savefig(out/(prefix+'-preload.png'),dpi=160);plt.close(fig)

    files = [sensitivity/'status.json',sensitivity/'resistance_report.json',sensitivity/'report.json',
             factorial/'status.json',factorial/'factorial_report.json',factorial/'report.json',factorial/'normalization-audit.json',
             spring/'pipeline-status.json',spring/'geometry-verification.json',spring/'selection.json',
             spring/'roundoff-followup-status.json',spring/'train/static/roundoff-audit.json',
             spring/'train/static/offline-report.json',spring/'offline-completion-status.json',validation_path,
             diag/'multigrasp-spring-preload/invalid-geometry-notice.json']
    evidence = dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    records={str(f.relative_to(root)):json.loads(f.read_text()) for f in files},
                    sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    (out/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    notes = f'''# Wuji knife resistance and contact diagnostics

Frozen teacher: `{crossed['checkpoint_sha256']}`.

Each damping condition uses the same first 20 development initial states. These are variations of one nominal grasp, not new geometries or 100/180 independent grasps. The factorial experiment varies actual and observed damping separately; off-diagonal conditions intentionally supply incorrect privileged information and are not proposed deployment policies.

At actual damping 0.3, changing only the observed value to 3 eliminates first-cycle success. At actual damping 3, keeping the observed value at 0.3 yields 20/20 first cycles, 16/20 stable first cycles and 6/20 joint full-rollout successes. The frozen normalizer represents observed damping 0.3 as zero, while both 3 and 30 saturate at +5. Thus changed privileged input is a major failure factor at damping 3. Actual damping 30 fails under every observed-value condition; no universal mechanical-infeasibility claim follows from this one policy.

The preload experiment holds targets with zero policy action. Nine settings use all 33 training grasps; selection maximizes full-rollout stable count, then minimizes target shift and setting index. The selected setting was frozen before evaluating all five held-out grasps: {stable}/5 stable for 20 seconds, {falls}/5 falls. This does not establish learned manipulation or knife operation.

Stability requires less than 10 mm body drift and 0.25 rad rotation throughout the 20-second rollout. Every endpoint held additionally requires less than 2 mm slider error during the last 0.3 seconds of every command window. Failures remain in the complete JSON records.

The first preload attempt used a mismatched object frame and is explicitly invalid. The corrected attempt completed physics but failed an overly strict target constancy assertion at 2.384e-6 rad. Its failed exit is preserved. A separate exact float32 recurrence audit explains each transition within one ULP; its report is separately identified. No trajectory or success threshold was changed.

These effective simulation values are not real knife calibration. The Sharpa paper calibrated candidate dynamics using teacher action replays on an independent real object; no such Wuji evidence is claimed here.
'''
    (out/(prefix+'-results.md')).write_text(notes)
    artifacts = sorted(out.glob(prefix+'-*'))
    (out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in artifacts if f.suffix!='.txt'))
    print(out)


if __name__ == '__main__':
    main()
