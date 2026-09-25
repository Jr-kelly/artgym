"""Offline phase/contact audit of executed trajectories; never runs physics."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.wuji_kinematics import WujiKinematics, FINGERS


def analyze(trial):
    trace = trial / 'trace.npz'
    if not trace.exists():
        trace = trial / 'partial-trace.npz'
    if not trace.exists():
        return dict(trial=trial.name, physical=False)
    t = np.load(trace)
    physics = json.loads((trial / 'physics.json').read_text())
    ids = physics['hand_indices']
    fk = WujiKinematics()
    pairs = [json.loads(line) for line in (trial / 'knife-contact-pairs.jsonl').read_text().splitlines()]
    rows = []
    for phase in dict.fromkeys(t['phase'].tolist()):
        steps = np.flatnonzero(t['phase'] == phase)
        last = int(steps[-1])
        obj = transform(t['object'][last, :3], t['object'][last, 3:])
        wrist = transform(t['wrist'][last, :3], t['wrist'][last, 3:])
        contacts = {}
        # Last 0.3 seconds, body-ordered local positions and normal signs.
        for digit in FINGERS:
            by_link = {}
            selected = [v for v in pairs if max(int(steps[0]), last-8) <= v['step'] <= last
                        and any('_'+digit+'_' in v['body'+str(s)] for s in [0, 1])]
            for v in selected:
                for side in [0, 1]:
                    body = v['body'+str(side)]
                    if body not in ['link_0', 'link_1']:
                        continue
                    dst = by_link.setdefault(body, dict(points=[], normals=[]))
                    key = 'localPos'+str(side)
                    if key in v:
                        dst['points'].append(v[key])
                    # PhysX normal points from body1 to body0; outward knife normal.
                    normal = np.asarray(v['normal']) * (-1 if side == 0 else 1)
                    rotation = Rotation.from_quat(t['object'][v['step'], 3:]).as_matrix()
                    dst['normals'].append(normal @ rotation)
            contacts[digit] = {
                body: dict(samples=len(v['normals']),
                           mean_outward_normal_object=np.mean(v['normals'], axis=0).tolist(),
                           mean_contact_position_link=np.mean(v['points'], axis=0).tolist() if v['points'] else None)
                for body, v in by_link.items()}
        cache = np.load('caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
        relative = np.linalg.inv(wrist) @ obj
        desired = transform(cache[40:43], cache[43:47])
        command = t['reference_targets'][steps][:, ids]
        rows.append(dict(phase=phase, start_s=float(t['time'][steps[0]]), end_s=float(t['time'][last]),
                         contact_fraction_thumb_index_middle_ring_pinky=(t['finger_knife_contacts'][steps] > 0).mean(0).tolist(),
                         contacts_last_03s=contacts,
                         measured_joint_limit_margin_rad=float(np.minimum(t['q'][steps]-fk.lower, fk.upper-t['q'][steps]).min()),
                         command_joint_limit_margin_rad=float(np.minimum(command-fk.lower, fk.upper-command).min()),
                         measured_joint_speed_max_rad_s=float(np.abs(t['dof_velocity'][steps][:, ids]).max()),
                         command_speed_max_rad_s=float(np.abs(np.diff(command, axis=0)).max()*30) if len(steps)>1 else 0.,
                         passive_slider_range_m=[float(t['slider'][steps].min()), float(t['slider'][steps].max())],
                         endpoint_object_in_hand=relative.tolist(),
                         endpoint_to_grasp0_position_m=float(np.linalg.norm(relative[:3, 3]-desired[:3, 3])),
                         endpoint_to_grasp0_rotation_rad=float(Rotation.from_matrix(desired[:3, :3].T@relative[:3, :3]).magnitude())))
    return dict(trial=trial.name, physical=True, phases=rows,
                conventions='xyzw; q/commands index,middle,pinky,ring,thumb; contacts thumb,index,middle,ring,pinky; localPos is actual collision contact. No force/torque inference from motor offsets or solver lambda.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        raise ValueError('Use a fresh output path; preserve prior audits.')
    results=[analyze(a.root / f.name[:-len('-process.json')]) for f in sorted(a.root.glob('*-process.json'))]
    a.output.write_text(json.dumps(results,indent=2)+'\n')
    print(str(a.output))


if __name__=='__main__':
    main()
