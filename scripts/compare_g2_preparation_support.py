"""Read actual continuous holding traces; contact occurrence is not force support."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def relative_pose(wrist, body):
    inv = Rotation.from_quat(wrist[:, 3:7]).inv()
    return np.concatenate((inv.apply(body[:, :3] - wrist[:, :3]),
                           (inv * Rotation.from_quat(body[:, 3:7])).as_quat()), axis=1)


def error(pose, reference):
    return (np.linalg.norm(pose[:, :3] - reference[:3], axis=1),
            (Rotation.from_quat(reference[3:7]).inv() * Rotation.from_quat(pose[:, 3:7])).magnitude())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figure', type=Path)
    args = parser.parse_args()
    rows = []
    boundaries = []
    curves = []
    for run in args.runs:
        t = np.load(run / 'trace.npz')
        report = json.loads((run / 'report.json').read_text())
        physics = json.loads((run / 'physics.json').read_text())
        names = physics['robot_dof_names']
        hand_indices = physics['hand_indices']
        phase = 'fixed_motor_hold' if report['args'].get('fixed_preparation_hold') else 'learned_hold'
        ids = np.flatnonzero(t['phase'] == phase)
        assert len(ids) == 660 and np.all(np.diff(ids) == 1)
        initial = int(ids[0]) - 1
        relative = relative_pose(t['wrist'], t['object'])
        world_m, world_rad = error(t['object'][ids], t['object'][initial])
        hand_m, hand_rad = error(relative[ids], relative[initial])
        time = np.arange(1, len(ids) + 1) / 30.
        bad = np.flatnonzero((world_m >= .01) | (world_rad >= .25))
        contacts = t['finger_knife_contacts'][ids] > 0
        curves.append((run.name, time, world_rad, contacts[:, 2]))
        per_finger = {}
        for finger, name in enumerate(['thumb', 'index', 'middle', 'ring', 'pinky']):
            motor_ids = [names.index('hand_r_%s_joint%d' % (name, j)) for j in range(1, 5)]
            measured_ids = [hand_indices.index(j) for j in motor_ids]
            absent = ~contacts[:, finger]
            windows = np.convolve(absent.astype(int), np.ones(9, dtype=int), mode='valid')
            sustained = np.flatnonzero(windows == 9)
            per_finger[name] = dict(contact_fraction=float(contacts[:, finger].mean()),
                first_absent_0p3s_window_start_s=float(time[sustained[0]]) if len(sustained) else None,
                measured_joint_change_max_rad=float(np.max(np.abs(t['q'][ids][:, measured_ids] - t['q'][initial, measured_ids]))),
                reference_change_max_rad=float(np.max(np.abs(t['reference_targets'][ids][:, motor_ids] - t['reference_targets'][initial, motor_ids]))))
        rows.append(dict(run=str(run),hold_phase=phase,frames=len(ids),
            world_drift_m=float(world_m.max()),world_rotation_rad=float(world_rad.max()),
            hand_relative_drift_m=float(hand_m.max()),hand_relative_rotation_rad=float(hand_rad.max()),
            first_world_instability_s=float(time[bad[0]]) if len(bad) else None,
            slider_passive_displacement_m=float(np.max(np.abs(t['slider'][ids]-t['slider'][initial]))),
            fingers=per_finger))
        boundaries.append((run.name, {k:t[k][initial].copy() for k in
            ['all_dof_position','dof_velocity','reference_targets','targets','object_rigid_state','slider_rigid_state','arm_integral_state']}))
    pairs = []
    for i in range(len(boundaries)):
        for j in range(i+1, len(boundaries)):
            a, b = boundaries[i], boundaries[j]
            pairs.append(dict(runs=[a[0],b[0]],initial_boundary_max_errors={k:float(np.max(np.abs(a[1][k]-b[1][k]))) for k in a[1]}))
    result = dict(scope='Read-only continuous H comparison, fixed start references in world and wrist coordinates',
        caveat='Contact counts indicate occurrence, not measured support force. Temporal association does not identify a unique failure cause.',
        rows=rows,initial_boundary_comparisons=pairs)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if args.figure:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True, constrained_layout=True)
        for name, time, rotation, contact in curves:
            axes[0].plot(time, rotation, label=name)
            # Trailing1s fraction; no invented contact before the first frame.
            sums = np.convolve(contact.astype(float), np.ones(30), mode='full')[:len(contact)]
            denominator = np.minimum(np.arange(1, len(contact)+1), 30)
            axes[1].plot(time, sums / denominator)
        axes[0].axhline(.25, color='firebrick', linestyle='--', label='Fixed-world rotation limit')
        axes[0].set_ylabel('Body rotation (rad)')
        axes[0].legend(fontsize=8)
        axes[1].set_ylabel('Middle contact fraction\n(trailing1s)')
        axes[1].set_xlabel('Time after actual hold takeover (s)')
        axes[1].set_ylim(-.03, 1.03)
        for ax in axes:
            ax.grid(alpha=.2)
        fig.suptitle('Actual continuous preparation: nominal versus seen00\nContact occurrence is not a measurement of support force')
        fig.savefig(args.figure, dpi=160)
        plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k != 'initial_boundary_comparisons'}))


if __name__ == '__main__':
    main()
