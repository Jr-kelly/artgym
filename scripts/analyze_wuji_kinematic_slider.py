"""Measure a no-slip thumb kinematic prior on existing labeled trajectories.

This diagnostic performs no fitting or simulation. Current object truth appears
only in labels and an explicitly privileged body-pose comparison. The usable
prior uses measured joints, the known acquisition pose, and a frozen estimator.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics, FINGERS

ROOT = Path(__file__).resolve().parents[1]
SCALES = np.array([.001, .001, .001, .02, .02, .02, .0005, .01])


def pad_poses(kinematics, normalized):
    """Vectorized NumPy URDF FK; order is the explicit configured DOF order."""
    shape = normalized.shape[:-1]
    q = ((normalized.reshape(-1, 20) + 1) / 2 *
         (kinematics.upper - kinematics.lower) + kinematics.lower)
    frames = {'hand_r_base_link': np.broadcast_to(np.eye(4), (len(q), 4, 4)).copy()}
    for parent, child, origin, index, axis in kinematics.joints:
        transform = np.broadcast_to(origin, (len(q), 4, 4)).copy()
        if index is not None:
            transform[:, :3, :3] = origin[:3, :3] @ Rotation.from_rotvec(q[:, index, None] * axis).as_matrix()
        frames[child] = frames[parent] @ transform
    result = np.stack([frames[f'hand_r_{finger}_pad_link'] for finger in FINGERS], axis=1)
    return result.reshape(shape + (5, 4, 4))


def contact_positions(kinematics, poses):
    points = np.stack([kinematics.contact_points[f] for f in FINGERS])
    return np.einsum('...fij,fj->...fi', poses[..., :3, :3], points) + poses[..., :3, 3]


def prior(initial, current_thumb, initial_thumb, displacement):
    shape = displacement.shape[:-1]
    r0 = Rotation.from_quat(initial[..., 23:27].reshape(-1, 4)).as_matrix().reshape(shape + (3, 3))
    delta = Rotation.from_rotvec(displacement[..., 3:6].reshape(-1, 3)).as_matrix().reshape(shape + (3, 3))
    rotation = delta @ r0
    pos = initial[..., 20:23] + displacement[..., :3]
    local0 = np.einsum('...ji,...j->...i', r0, initial_thumb-initial[..., 20:23])
    local = np.einsum('...ji,...j->...i', rotation, current_thumb-pos)
    # Acquisition-frame prismatic axis is -Y. Contact is assumed to stick.
    return local0[..., 1]-local[..., 1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    manifest = json.loads(args.dataset.with_name('manifest.json').read_text())
    assert hashlib.sha256(args.dataset.read_bytes()).hexdigest() == manifest['dataset_sha256']
    with np.load(args.dataset) as z:
        x = z['features'][:, z['label_steps']].astype(np.float64)
        target = z['target'].astype(np.float64)
        active, training, rows = z['active'], z['train_rows'], z['initial_rows']
    assert x.shape == (4, 150, 90, 103) and active.all()
    kin = WujiKinematics()
    initial = x[..., 40:95]
    poses = pad_poses(kin, x[..., :20])
    initial_poses = pad_poses(kin, initial[..., :20])
    current = contact_positions(kin, poses)[..., 0, :]
    first = contact_positions(kin, initial_poses)[..., 0, :]
    # Independent scalar FK must match the batched implementation.
    max_scalar = 0.
    for s, t, row in [(0, 0, 0), (0, 149, 29), (1, 30, 45), (2, 81, 75), (3, 143, 89)]:
        norm = x[s, t, row, :20]
        q = (norm+1)/2*(kin.upper-kin.lower)+kin.lower
        scalar = kin.forward(q)
        expected = np.stack([scalar[f'hand_r_{f}_pad_link'] for f in FINGERS])
        max_scalar = max(max_scalar, float(np.max(np.abs(expected-poses[s,t,row]))))
    assert max_scalar < 1e-12
    # The acquisition fields contain recorded pad-link origins in hand frame.
    init_fk_error = initial_poses[..., :3, 3]-initial[..., 34:49].reshape(4,150,90,5,3)
    predictions = {
        'frozen_tcn': x[..., 101]*SCALES[6],
        'fixed_initial_body_no_slip': prior(initial,current,first,np.zeros_like(target)),
        'estimated_body_no_slip': prior(initial,current,first,x[..., 95:103]*SCALES),
        'true_body_no_slip_DIAGNOSTIC': prior(initial,current,first,target),
    }
    stats = {}
    for name, prediction in predictions.items():
        err = prediction-target[..., 6]
        stats[name] = {}
        for s, key in enumerate(['teacher2','teacher5','student2','student5']):
            stats[name][key] = {}
            for split, mask in [('training',training),('validation',~training)]:
                e = err[s][:,mask]
                stats[name][key][split] = dict(rmse_mm=float(np.sqrt(np.mean(e**2))*1000),
                    bias_mm=float(e.mean()*1000), absolute_q50_q90_q99_mm=(np.quantile(np.abs(e),[.5,.9,.99])*1000).tolist(),
                    samples=int(e.size),by_grasp_rmse_mm=[float(np.sqrt(np.mean(err[s][:,mask & (rows//100==g)]**2))*1000) for g in range(3)])
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        dataset_sha256=manifest['dataset_sha256'], no_fit=True, no_physics=True,
        scope=__doc__, scalar_batch_fk_max_error=max_scalar,
        initial_pad_origin_max_error_m=float(np.abs(init_fk_error).max()),
        initial_pad_origin_rmse_m=float(np.sqrt(np.mean(init_fk_error**2))),
        statistics=stats, training_rows=rows[training].tolist(),validation_rows=rows[~training].tolist(),
        geometry_sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),ROOT/'scripts/wuji_kinematics.py',ROOT/kin.config['asset']]},
        limitations='No-slip fixed point ignores rolling, slip, compliance and hand calibration. Both validation and training states are existing development data; this is not task success.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{s:round(v[s]['validation']['rmse_mm'],4) for s in v} for k,v in stats.items()}))
    print(json.dumps({k:result[k] for k in ['scalar_batch_fk_max_error','initial_pad_origin_max_error_m','initial_pad_origin_rmse_m']}))


if __name__ == '__main__':
    main()
