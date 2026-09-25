"""URDF forward/inverse kinematics for the ArtBot Wuji hand, in metres/radians."""
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import yaml


ROOT = Path(__file__).resolve().parents[1]
FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')


class WujiKinematics:
    def __init__(self):
        self.config = yaml.safe_load((ROOT / 'isaacgymenvs/cfg/hand/wuji.yaml').read_text())
        self.names = self.config['dof_names']
        robot = ET.parse(ROOT / self.config['asset']).getroot()
        self.joints = []
        self.lower, self.upper = np.zeros(20), np.zeros(20)
        for joint in robot.findall('joint'):
            origin = joint.find('origin')
            transform = np.eye(4)
            if origin is not None:
                transform[:3, 3] = np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
                transform[:3, :3] = Rotation.from_euler('xyz', np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')).as_matrix()
            index, axis = None, None
            if joint.get('type') == 'revolute':
                index = self.names.index(joint.get('name'))
                axis = np.fromstring(joint.find('axis').get('xyz'), sep=' ')
                limit = joint.find('limit')
                self.lower[index], self.upper[index] = float(limit.get('lower')), float(limit.get('upper'))
            self.joints.append((joint.find('parent').get('link'), joint.find('child').get('link'), transform, index, axis))
        self.contact_points = {}
        for finger in FINGERS:
            name = f'hand_r_{finger}_pad_link'
            path = ROOT / Path(self.config['asset']).parent / 'meshes/collision' / f'{name}.obj'
            vertices = np.array([np.fromstring(line[2:], sep=' ') for line in path.read_text().splitlines() if line.startswith('v ')])
            point = vertices.mean(axis=0)
            point[0] = vertices[:, 0].max()
            self.contact_points[finger] = point

    def forward(self, qpos):
        frames = {'hand_r_base_link': np.eye(4)}
        for parent, child, origin, index, axis in self.joints:
            transform = origin.copy()
            if index is not None:
                transform[:3, :3] = transform[:3, :3] @ Rotation.from_rotvec(axis * qpos[index]).as_matrix()
            frames[child] = frames[parent] @ transform
        return frames

    def contacts(self, qpos):
        frames = self.forward(qpos)
        points, normals = [], []
        for finger in FINGERS:
            t = frames[f'hand_r_{finger}_pad_link']
            points.append(t[:3, :3] @ self.contact_points[finger] + t[:3, 3])
            normals.append(t[:3, 0])
        return np.asarray(points), np.asarray(normals)

    def solve_finger(self, finger, target, initial, normal=None):
        # SciPy estimates a Jacobian using ~1e-8 perturbations. Keeping the
        # simulation's float32 input here silently rounds those changes away.
        initial = np.asarray(initial, dtype=np.float64)
        index = FINGERS.index(finger)
        indices = [self.names.index(f'hand_r_{finger}_joint{i}') for i in range(1, 5)]
        def residual(values):
            qpos = initial.copy()
            qpos[indices] = values
            points, normals = self.contacts(qpos)
            errors = [(points[index] - target) * 100]
            if normal is not None:
                errors.append((normals[index] - normal) * 0.25)
            return np.concatenate(errors)
        result = least_squares(residual, np.clip(initial[indices], self.lower[indices] + 1e-6, self.upper[indices] - 1e-6),
                               bounds=(self.lower[indices], self.upper[indices]), max_nfev=100)
        qpos = initial.copy()
        qpos[indices] = result.x
        return qpos, float(np.linalg.norm(self.contacts(qpos)[0][index] - target))


if __name__ == '__main__':
    hand = WujiKinematics()
    for flex in (0, 0.4, 0.8, 1.2):
        q = np.array([0 if name.endswith('joint2') else flex for name in hand.names])
        q = np.clip(q, hand.lower, hand.upper)
        points, normals = hand.contacts(q)
        print('Flex:', flex)
        for finger, point, normal in zip(FINGERS, points, normals):
            print(finger, 'contact', point.round(4), 'normal', normal.round(3))
