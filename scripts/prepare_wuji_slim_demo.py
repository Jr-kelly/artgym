"""Build a scripted preview using the NT reference geometry and validated grasps.

Preview output is separate from the paper assets/caches. The coordinate change
maps paper (width, thickness, length) to demo (width, -length, thickness), and
shifts the slider's lower limit to zero without changing its physical position.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from scripts.build_wuji_knife_demo import GraspBuilder, box_link
from scripts.refine_wuji_knife_grasp import thumb_contact
from scripts.wuji_kinematics import ROOT


def prepare(output):
    source = ROOT/'assets/objects/knife_wuji_paper/000'
    meta = json.loads((source/'parameters.json').read_text())
    folder = output/'asset'
    folder.mkdir(parents=True, exist_ok=True)
    transform = Rotation.from_euler('x', -90, degrees=True)
    handle = np.asarray(meta['handle_size'])[[0, 2, 1]]
    slider = np.asarray(meta['slider_size'])[[0, 2, 1]]
    origin = transform.inv().apply(meta['slider_initial_center'])
    robot = ET.Element('robot', name='nt_a300gr_scripted_preview')
    box_link(robot, 'link_0', handle, meta['masses'][0], '.58 .60 .64 1')
    moving = box_link(robot, 'link_1', slider, meta['masses'][1], '.12 .13 .15 1')
    blade = ET.SubElement(moving, 'visual')
    blade_center = np.array([0., -handle[1]/2 + .020, 0.]) - origin
    ET.SubElement(blade, 'origin', xyz=' '.join(map(str, blade_center)))
    ET.SubElement(ET.SubElement(blade, 'geometry'), 'box', size='.009 .040 .0005')
    material = ET.SubElement(blade, 'material', name='visual_only_blade')
    ET.SubElement(material, 'color', rgba='.75 .79 .84 1')
    joint = ET.SubElement(robot, 'joint', name='slider', type='prismatic')
    ET.SubElement(joint, 'parent', link='link_0')
    ET.SubElement(joint, 'child', link='link_1')
    ET.SubElement(joint, 'origin', xyz=' '.join(map(str, origin)))
    ET.SubElement(joint, 'axis', xyz='0 -1 0')
    ET.SubElement(joint, 'limit', lower='0', upper=str(meta['joint_upper']-meta['joint_lower']), effort='100', velocity='1')
    ET.SubElement(joint, 'dynamics', damping='.3', friction='.001')
    ET.indent(robot) if hasattr(ET, 'indent') else None
    ET.ElementTree(robot).write(folder/'mobility.urdf', encoding='utf-8', xml_declaration=True)
    preview = dict(handle_size=handle.tolist(), slider_size=slider.tolist(), slider_origin=origin.tolist(),
                   masses=meta['masses'], total_size_lwt=meta['total_size_lwt'], travel=.05,
                   source_urdf_sha256=hashlib.sha256((source/'mobility.urdf').read_bytes()).hexdigest(),
                   assumptions=['Scripted contact preview, not a trained policy',
                                'Geometry and mass match NT paper anchor; blade is visual only',
                                'Passive damping 0.3 is the preview setting, not paper damping 1000',
                                'No latch or cutting simulation'])
    (folder/'parameters.json').write_text(json.dumps(preview, indent=2))
    data = np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_paper/000/valid_grasps.npy')
    rotations = (Rotation.from_quat(data[:, 43:47]) * transform).as_quat()
    np.savez(output/'candidates.npz', qpos=data[:, :20], targets=data[:, 20:40],
             centers=data[:, 40:43], rotations=rotations, slider=data[:, 54]-meta['joint_lower'],
             paper_grasp_ids=np.arange(len(data)))
    print('Prepared', len(data), 'grasps; overall dimensions mm', np.array(meta['total_size_lwt'])*1000, flush=True)


def plan(args):
    output = args.output
    meta = json.loads((output/'asset/parameters.json').read_text())
    b = GraspBuilder(meta)
    source = np.load(output/'candidates.npz')
    rollout = np.load(output/'hold/rollout.npz')
    report = json.loads((output/'hold/report.json').read_text())
    eligible = [r for r in report['ranked'] if r['max_drift_m'] < .01 and r['final_rotation_rad'] < .3]
    if args.thumb_side:
        eligible = [r for r in eligible if Rotation.from_quat(source['rotations'][r['candidate']]).apply([0,-1,0])[1]>.7]
    eligible.sort(key=lambda r: (-sum(r['contact_fraction'][1:]), r['max_drift_m']))
    hand_r = Rotation.from_quat([.5, -.5, .5, .5])
    times = np.linspace(0, 12, 49)
    paths, initial, commands, centers, rotations, sliders, provenance = [], [], [], [], [], [], []
    for entry in eligible[:args.count]:
        index = int(np.where(rollout['candidate_ids'] == entry['candidate'])[0][0])
        state = rollout['states'][-1, index]
        center = hand_r.inv().apply(state[1:4]-[0, 0, .5])
        rotation = hand_r.inv()*Rotation.from_quat(state[4:8])
        command = source['targets'][entry['candidate']].copy()
        for depth in args.depth:
            for offset in args.offset:
                q, qs, errors = command.copy(), [], []
                for t in times:
                    if t < 1: s = state[-1]
                    elif t < 5: s = state[-1]+(.043-state[-1])*(1-np.cos(np.pi*(t-1)/4))/2
                    elif t < 6: s = .043
                    elif t < 10: s = .043+(-.003-.043)*(1-np.cos(np.pi*(t-6)/4))/2
                    else: s = -.003
                    q, error = thumb_contact(b, q, center, rotation.as_matrix(), s, depth, (0, offset))
                    if t < 1:
                        alpha = (1-np.cos(np.pi*t))/2
                        q = command*(1-alpha)+q*alpha
                    qs.append(q.copy()); errors.append(error)
                initial.append(state[14:-1]); commands.append(command); centers.append(center)
                rotations.append(rotation.as_quat()); sliders.append(state[-1]); paths.append(qs)
                provenance.append(dict(source_grasp_id=entry['candidate'],
                                       source='resized_reference_ik' if (output/'seeds.json').exists() else 'paper_valid_pool',
                                       depth=depth, offset=offset,
                                       max_ik_error_m=max(errors)))
                print('path', len(paths)-1, provenance[-1], flush=True)
    if not paths:
        raise RuntimeError('No stable held grasps available')
    np.savez(output/'initial.npz', qpos=initial, targets=commands, centers=centers,
             rotations=rotations, slider=sliders)
    np.savez(output/'trajectory.npz', time=times, qpos=np.asarray(paths).transpose(1, 0, 2))
    (output/'paths.json').write_text(json.dumps(provenance, indent=2))


def seed(output):
    """Re-solve all fingers for the slim body around the earlier grip orientation."""
    b = GraspBuilder(json.loads((output/'asset/parameters.json').read_text()))
    reference = yaml.safe_load((ROOT/'assets/demo/wuji_knife/preset.yaml').read_text())['initial']
    h = b.hand
    r = Rotation.from_quat(reference['rotations'])
    normal = r.as_matrix()[:, 2]
    qs, centers, rotations, settings = [], [], [], []
    for shift in (0., .006, .012):
        for dz in (-.006, 0., .006):
            center = np.array(reference['centers'])+normal*shift+[0, 0, dz]
            q = np.array(reference['targets'])
            errors = []
            for finger, y in [('index', .025), ('middle', .007), ('ring', -.013), ('pinky', -.032)]:
                ids = [h.names.index(f'hand_r_{finger}_joint{i}') for i in range(1, 5)]
                target = center+r.apply([-.0075, y, .004-.0007])
                verts = b.vertices[f'hand_r_{finger}_pad_link']
                def residual(values):
                    pose = q.copy(); pose[ids] = values
                    frame = h.forward(pose)[f'hand_r_{finger}_pad_link']
                    v = verts@frame[:3, :3].T+frame[:3, 3]
                    point = v.mean(0)
                    point += normal*((v@normal).min()-point@normal)
                    return np.r_[(point-target)*100, (frame[:3, 0]+normal)*.08]
                fit = least_squares(residual, np.clip(q[ids], h.lower[ids]+1e-7, h.upper[ids]-1e-7),
                                    bounds=(h.lower[ids], h.upper[ids]), max_nfev=100)
                q[ids] = fit.x; errors.append(np.linalg.norm(fit.fun[:3])/100)
            q, error = thumb_contact(b, q, center, r.as_matrix(), 0., .0015, (0., .006))
            errors.append(error)
            qs.append(q); centers.append(center); rotations.append(r.as_quat())
            settings.append(dict(shift=shift, dz=dz, errors_m=errors))
            print(len(qs)-1, settings[-1], flush=True)
    np.savez(output/'candidates.npz', qpos=qs, targets=qs, centers=centers,
             rotations=rotations, slider=np.zeros(len(qs)))
    (output/'seeds.json').write_text(json.dumps(settings, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['prepare', 'plan', 'seed'])
    p.add_argument('--output', type=Path, default=ROOT/'tmp/wuji-slim-demo')
    p.add_argument('--count', type=int, default=12)
    p.add_argument('--depth', type=float, nargs='+', default=[.0015])
    p.add_argument('--offset', type=float, nargs='+', default=[-.006, .006])
    p.add_argument('--thumb-side', action='store_true', help='Select blade direction toward the thumb/index side')
    args = p.parse_args()
    if args.stage == 'prepare': prepare(args.output)
    elif args.stage == 'seed': seed(args.output)
    else: plan(args)


if __name__ == '__main__':
    main()
