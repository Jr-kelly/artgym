"""Generate a parameterized two-link utility knife and Wuji grasp candidates.

All dimensions are metres. The knife has no latch; only contact forces move its
passive prismatic joint. Generated assets and candidates are local build output.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares

from scripts.wuji_kinematics import ROOT, FINGERS, WujiKinematics


def box_link(robot, name, size, mass, color):
    link = ET.SubElement(robot, 'link', name=name)
    inertial = ET.SubElement(link, 'inertial')
    ET.SubElement(inertial, 'mass', value=str(mass))
    x, y, z = size
    ET.SubElement(inertial, 'inertia', ixx=str(mass*(y*y+z*z)/12),
                  iyy=str(mass*(x*x+z*z)/12), izz=str(mass*(x*x+y*y)/12),
                  ixy='0', ixz='0', iyz='0')
    for tag in ('visual', 'collision'):
        element = ET.SubElement(link, tag)
        geom = ET.SubElement(element, 'geometry')
        ET.SubElement(geom, 'box', size=' '.join(map(str, size)))
        if tag == 'visual':
            material = ET.SubElement(element, 'material', name=name+'_color')
            ET.SubElement(material, 'color', rgba=color)
    return link


def build_asset(output, width=.032, length=.14, thickness=.022, travel=.04):
    if min(width, length, thickness, travel) <= 0 or travel >= length:
        raise ValueError('Knife dimensions must be positive and travel shorter than handle length')
    output.mkdir(parents=True, exist_ok=True)
    robot = ET.Element('robot', name='wuji_knife_demo')
    handle_size = [width, length, thickness]
    slider_size = [.022, .024, .006]
    box_link(robot, 'link_0', handle_size, .08, '.92 .48 .06 1')
    slider = box_link(robot, 'link_1', slider_size, .01, '.12 .15 .19 1')
    # Visual blade belongs to the moving link. Collision is intentionally the
    # two-box approximation used by ArtManip, with no cutting interaction.
    visual = ET.SubElement(slider, 'visual')
    ET.SubElement(visual, 'origin', xyz=f'0 {-length/2-.01} {-thickness/2-.003}')
    ET.SubElement(ET.SubElement(visual, 'geometry'), 'box', size='.018 .035 .001')
    material = ET.SubElement(visual, 'material', name='blade')
    ET.SubElement(material, 'color', rgba='.75 .79 .84 1')
    joint = ET.SubElement(robot, 'joint', name='slider_joint', type='prismatic')
    ET.SubElement(joint, 'parent', link='link_0')
    ET.SubElement(joint, 'child', link='link_1')
    ET.SubElement(joint, 'origin', xyz=f'0 .025 {thickness/2+.003}')
    ET.SubElement(joint, 'axis', xyz='0 -1 0')
    ET.SubElement(joint, 'limit', lower='0', upper=str(travel), effort='20', velocity='.2')
    ET.SubElement(joint, 'dynamics', damping='.3', friction='0')
    ET.ElementTree(robot).write(output/'mobility.urdf', encoding='utf-8', xml_declaration=True)
    (output.parent/'lbx.json').write_text(json.dumps({output.name: handle_size+slider_size}, indent=2))
    metadata = dict(handle_size=handle_size, slider_size=slider_size, travel=travel,
                    slider_origin=[0, .025, thickness/2+.003], masses=[.08, .01],
                    assumptions=['direct sliding without a latch', 'two-box collision model',
                                 'visual blade has no cutting physics'])
    (output/'parameters.json').write_text(json.dumps(metadata, indent=2))
    return metadata


class GraspBuilder:
    def __init__(self, metadata):
        self.hand = WujiKinematics()
        self.meta = metadata
        self.vertices = {}
        mesh_dir = ROOT/'assets/hands/wuji_artbot/meshes/collision'
        for path in mesh_dir.glob('*.obj'):
            self.vertices[path.stem] = np.array([np.fromstring(line[2:], sep=' ') for line in path.read_text().splitlines() if line.startswith('v ')])

    def solve(self, center, contact_x, contact_z, thumb_y, preload=.0005):
        h = self.hand
        q = np.clip(np.array([0 if n.endswith('joint2') else 1.2 for n in h.names]), h.lower, h.upper)
        errors = []
        for finger in FINGERS:
            is_thumb = finger == 'thumb'
            index = FINGERS.index(finger)
            ids = [h.names.index(f'hand_r_{finger}_joint{i}') for i in range(1, 5)]
            y = dict(index=.025, middle=.006, ring=-.015, pinky=-.034).get(finger, thumb_y)
            target = np.array([contact_x, y, contact_z])
            direction = np.array([0., 0., 1.])
            if is_thumb:
                target = center + np.array([0, thumb_y, self.meta['handle_size'][2]/2+.006])
                direction[2] = -1
            q, _ = h.solve_finger(finger, target, q, direction)
            pad = f'hand_r_{finger}_pad_link'
            def residual(values):
                pose = q.copy(); pose[ids] = values
                frames = h.forward(pose)
                t = frames[pad]
                v = self.vertices[pad] @ t[:3, :3].T + t[:3, 3]
                # Surface support along the desired contact normal, with a
                # small preload. Match tangential position using pad centroid.
                point = v.mean(0)
                point[2] = v[:,2].min() if is_thumb else v[:,2].max()
                e = [(point-target-direction*preload)*100]
                e.append((t[:3,0]-direction)*.12)
                # Discourage other parts of this digit starting inside handle.
                half = np.asarray(self.meta['handle_size'])/2
                for link in (f'hand_r_{finger}_link{i}' for i in (1,2,3,4)):
                    t2 = frames[link]
                    v2 = self.vertices[link] @ t2[:3,:3].T+t2[:3,3]
                    sdf = np.max(np.abs(v2-center)-half, axis=1)
                    e.append(np.minimum(sdf+.0003, 0)*150)
                return np.concatenate(e)
            fit = least_squares(residual, np.clip(q[ids], h.lower[ids]+1e-7, h.upper[ids]-1e-7),
                                bounds=(h.lower[ids],h.upper[ids]),max_nfev=80)
            q[ids] = fit.x
            errors.append(float(np.linalg.norm(fit.fun[:3])/100))
        return q, errors

    def solve_surface(self, finger, target, outward, initial, center, rotation, clearance=0):
        h=self.hand
        q,_=h.solve_finger(finger,target,initial,-outward)
        ids=[h.names.index(f'hand_r_{finger}_joint{i}') for i in range(1,5)]
        pad=f'hand_r_{finger}_pad_link'
        def residual(values):
            pose=q.copy();pose[ids]=values;frames=h.forward(pose)
            t=frames[pad];v=self.vertices[pad]@t[:3,:3].T+t[:3,3]
            point=v.mean(0);point+=outward*(np.min(v@outward)-point@outward)
            e=[(point-target-outward*clearance)*100,(t[:3,0]+outward)*.08]
            half=np.array(self.meta['handle_size'])/2
            for i in (1,2,3,4):
                name=f'hand_r_{finger}_link{i}';t2=frames[name]
                v2=(self.vertices[name]@t2[:3,:3].T+t2[:3,3]-center)@rotation
                sdf=np.max(np.abs(v2)-half,axis=1)
                e.append(np.minimum(sdf,0)*50)
            return np.concatenate(e)
        fit=least_squares(residual,np.clip(q[ids],h.lower[ids]+1e-7,h.upper[ids]-1e-7),
                          bounds=(h.lower[ids],h.upper[ids]),max_nfev=70)
        q[ids]=fit.x
        return q,float(np.linalg.norm(fit.fun[:3])/100)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'assets/objects/knife_wuji_demo/000')
    parser.add_argument('--candidates', type=Path, default=ROOT/'tmp/knife-demo/candidates.npz')
    parser.add_argument('--travel', type=float, default=.04)
    parser.add_argument('--width', type=float, default=.032)
    parser.add_argument('--length', type=float, default=.14)
    parser.add_argument('--thickness', type=float, default=.022)
    args = parser.parse_args()
    meta = build_asset(args.output, args.width, args.length, args.thickness, args.travel)
    builder = GraspBuilder(meta)
    qs, centers, errors, parameters = [], [], [], []
    for x in (.026, .034, .042):
        for z in (.080, .088, .096):
            for edge in (.002, .008):
                center = np.array([x, 0., z])
                q, err = builder.solve(center, x+edge, z-meta['handle_size'][2]/2, .025)
                for preload in (0., .02, .05):
                    # Bias flexion to retain contact after settling.
                    target = q.copy()
                    for f in FINGERS[1:]:
                        target[builder.hand.names.index(f'hand_r_{f}_joint4')] += preload
                    qs.append(np.clip(target, builder.hand.lower, builder.hand.upper))
                    centers.append(center); errors.append(err); parameters.append([x,z,edge,preload])
                print('candidate', len(qs), [x,z,edge], 'IK error mm', np.round(np.array(err)*1000,2), flush=True)
    args.candidates.parent.mkdir(parents=True,exist_ok=True)
    np.savez(args.candidates, qpos=qs, centers=centers, errors=errors, parameters=parameters)
    print('Saved',len(qs),'candidates to',args.candidates)


if __name__ == '__main__':
    main()
