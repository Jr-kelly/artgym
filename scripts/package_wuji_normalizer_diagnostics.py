"""Package normalization-only counterfactuals and new grasp quality evidence."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    output = base / 'release-normalizer-diagnostics-20260922'
    output.mkdir(parents=True, exist_ok=True)
    prefix = 'wuji-knife-normalizer-diagnostics-20260922'
    folder = base / 'diagnostics/functional20-normalizer-update-sensitivity'
    status = json.loads((folder / 'status.json').read_text())
    data = json.loads((folder / 'report.json').read_text())
    assert status['status'] == data['status'] == 'completed' and status['returncode'] == 0
    assert data['all_model_tensors_restored'] and data['learned_weights_unchanged']
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for size, color in [(256, '#3678ad'), (8192, '#bc632a')]:
        rows = sorted([row for row in data['records'] if row['update_observations'] == size], key=lambda row: row['initial_count'])
        counts = [row['initial_count'] for row in rows]
        axes[0].loglog(counts, [row['gaussian_kl_mean'] for row in rows], 'o-', color=color, label=f'{size} observations')
        axes[1].semilogx(counts, [row['clipped_thumb_abs_change_mean'] for row in rows], 'o-', color=color, label=f'{size} observations')
    axes[0].set(xlabel='Initial normalization sample count', ylabel='Mean Gaussian KL (sum across 20 actions)', title='Policy change with no learned-weight update')
    axes[1].set(xlabel='Initial normalization sample count', ylabel='Mean absolute thumb action change', ylim=(0, .65), title='Clipped actions, same input and zero RNN state')
    for axis in axes:
        axis.legend(title='One statistics update')
        axis.grid(alpha=.2)
    fig.suptitle('Frozen single-grasp teacher on 256 stored training observations from functional20\nPreprocessing counterfactual only: no PPO, no physics steps, no held-out manipulation result', fontsize=11)
    fig.savefig(output / (prefix + '-normalization-only.png'), dpi=160)
    plt.close(fig)
    paths = [folder / 'status.json', folder / 'report.json',
             base / 'functional27-dataset-manifest.json',
             base / 'diagnostics/functional27-grasp-separation.json',
             base / 'diagnostics/functional27-continuity.json']
    generations = ['fresh-lowgain-functional-generation/independent-quality-v2',
                   'fresh-lowgain-functional-generation-seed19/independent-quality',
                   'fresh-lowgain-functional-generation-seed20/independent-quality']
    reports = [json.loads((base / 'diagnostics' / name / 'report.json').read_text()) for name in generations]
    paths += [base / 'diagnostics' / name / 'report.json' for name in generations]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    positions = np.arange(3)
    for offset, key, label, color in [(-.24, 'first_stage_valid', 'After 1 s physics', '#7895b7'),
                                      (0., 'train', 'Final training grasps', '#328776'),
                                      (.24, 'test', 'Final held-out grasps', '#bb682d')]:
        values = [sum(row['counts'][split][key] for split in ['train', 'test']) if key == 'first_stage_valid'
                  else row['counts'][key]['accepted'] for row in reports]
        bars = axes[0].bar(positions + offset, values, .24, color=color, label=label)
        axes[0].bar_label(bars)
    axes[0].set(xticks=positions, xticklabels=['Seed 20261018', 'Seed 20261019', 'Seed 20261020'],
                ylabel='Grasps retained', ylim=(0, 53), title='1,000 raw candidates for each seed')
    axes[0].legend(fontsize=8)
    continuity = json.loads((base / 'diagnostics/functional27-continuity.json').read_text())
    values = [continuity['counts'][split]['continuous_pass'] for split in ['train', 'test']]
    totals = [continuity['counts'][split]['total'] for split in ['train', 'test']]
    bars = axes[1].bar([0, 1], totals, color='#d7dfe3', label='Legacy reach + physical gates')
    passed = axes[1].bar([0, 1], values, color='#328776', label='Complete anchored path')
    axes[1].bar_label(passed, labels=[f'{value}/{total}' for value, total in zip(values, totals)])
    axes[1].set(xticks=[0, 1], xticklabels=['Training', 'Held-out'], ylim=(0, 33),
                ylabel='Grasps', title='New frozen pool: 27 training / 2 held-out')
    axes[1].legend(fontsize=8)
    fig.suptitle('Same 147 x 19 x 11 mm knife; all rejected candidates remain in source reports\nContinuity is a separate kinematic diagnostic, with no relabeling and no policy-success claim', fontsize=11)
    fig.savefig(output / (prefix + '-grasp-quality.png'), dpi=160)
    plt.close(fig)
    payload = dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   records={str(path.relative_to(root)): json.loads(path.read_text()) for path in paths},
                   sha256={str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
    (output / (prefix + '-all-records-provenance.json')).write_text(json.dumps(payload, indent=2) + '\n')
    (output / (prefix + '-results.md')).write_text('''# Normalization and functional-grasp diagnostics

With the teacher weights fixed, one normalization update using 256 training observations produces mean Gaussian KL 9.415 when the previous sample count is reset to 1, versus 0.000028 with the original count 39,321,601. With 8,192 update observations the corresponding values are 13.371 and 0.00809. Identical probe observations and zero recurrent states are used. All model tensors are restored after each condition. The plots also report changes after clipping to the legal action range. This isolates a preprocessing-induced policy change; it does not show that any count is optimal, reproduce a full PPO update, or prove the sole cause of multi-grasp failure.

The three new 1,000-candidate batches retain 24, 43 and 29 grasps after the one-second physics filter. Applying the unchanged posture, closed-slider, 40 mm reach, 20-second stability and five-finger semantic-contact gates retains training/test counts 3/1, 4/1 and 3/0. Rejected rows remain in the reports. Adding seven training and one test row to the earlier frozen 20/1 pool creates a separate 27/2 pool; ongoing functional20 experiments remain unchanged. This is one knife geometry, not 27 objects.

The new held-out row has a nearby object pose in training (0.524 mm, 0.0244 rad) but a substantially different hand configuration (joint RMS difference 0.738 rad). The earlier held-out row is farther from training poses. Exact row overlap is zero. These proximity results are descriptive; two held-out grasps are insufficient for broad generalization claims.

The legacy reach solver may start from a thumb posture different from the actual initial state. A separate fixed-material-contact-point, bounded-step IK probe finds continuous 40 mm opening/closing paths for 23/27 training and 2/2 held-out rows, using the actual initial thumb joints. The four unsuccessful local IK searches are retained; they do not prove mechanical impossibility. A successful path does not establish physical sticking contact or policy success. A separate free-object physical replay is queued for the 23 training rows; no held-out row is replayed by it.

All these results are simulations or offline diagnostics. Official Wuji per-joint gains and armatures are used with ArtBot geometry and PhysX; real actuator, contact and knife-resistance calibration remains outstanding.
''')
    files = sorted(output.glob(prefix + '-*'))
    (output / (prefix + '-SHA256SUMS.txt')).write_text(''.join(
        hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
        for path in files if path.suffix != '.txt'))
    print(output)


if __name__ == '__main__':
    main()
