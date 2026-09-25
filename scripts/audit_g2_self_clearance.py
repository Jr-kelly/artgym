"""Offline sampled convex arm/palm self-clearance audit; no physics changes.

Uses actual joint traces. Source self-collision remains disabled; a clear sample
audit is not a continuous collision certificate. Excludes links within two graph
edges (joint housings/mount seams) and does not test finger self-contact here.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import ROOT, G2Kinematics


def unique_directions(v):
    length = np.linalg.norm(v, axis=1)
    v = v[length > 1e-9] / length[length > 1e-9, None]
    pivot = np.argmax(abs(v), axis=1)
    v *= np.sign(v[np.arange(len(v)), pivot])[:, None]
    return np.unique(np.round(v, 7), axis=0)


def maximum_gap(va, vb, axes):
    maximum = -np.inf
    for begin in range(0, len(axes), 256):
        axis = axes[begin:begin + 256]
        length = np.linalg.norm(axis, axis=1)
        axis = axis[length > 1e-9] / length[length > 1e-9, None]
        if not len(axis):
            continue
        pa, pb = va @ axis.T, vb @ axis.T
        gap = np.maximum(pa.min(0) - pb.max(0), pb.min(0) - pa.max(0))
        maximum = max(maximum, float(gap.max()))
        if maximum >= -.0001:
            break
    return maximum


class Clearance:
    def __init__(self):
        self.k = G2Kinematics()
        path = ROOT / 'assets/robots/g2_wuji/g2_wuji.urdf'
        xml = ET.parse(path).getroot()
        joints = list(xml.findall('joint'))
        self.frames = {'base_link': np.eye(4)}
        self.graph = {}
        for joint in joints:
            a, b = joint.find('parent').get('link'), joint.find('child').get('link')
            self.graph.setdefault(a, set()).add(b)
            self.graph.setdefault(b, set()).add(a)
        while joints:
            ready = [j for j in joints if j.find('parent').get('link') in self.frames]
            assert ready, 'Disconnected G2 model'
            for joint in ready:
                origin = joint.find('origin')
                t = np.eye(4)
                if origin is not None:
                    t[:3, :3] = Rotation.from_euler('xyz', np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')).as_matrix()
                    t[:3, 3] = np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
                self.frames[joint.find('child').get('link')] = self.frames[joint.find('parent').get('link')] @ t
                joints.remove(joint)
        self.meshes = {}
        for link in xml.findall('link'):
            name = link.get('name')
            if name.startswith('hand_r_') and name != 'hand_r_base_link':
                continue
            for col in link.findall('collision'):
                mesh = col.find('geometry/mesh')
                assert mesh is not None
                v = np.array([np.fromstring(line[2:], sep=' ') for line in
                              (path.parent / mesh.get('filename')).read_text().splitlines() if line.startswith('v ')])
                v *= np.fromstring(mesh.get('scale', '1 1 1'), sep=' ')
                origin = col.find('origin')
                if origin is not None:
                    rotation = Rotation.from_euler('xyz', np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')).as_matrix()
                    v = v @ rotation.T + np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
                hull = ConvexHull(v)
                edges = np.concatenate([v[hull.simplices[:, a]] - v[hull.simplices[:, b]] for a, b in [(0, 1), (1, 2), (2, 0)]])
                self.meshes.setdefault(name, []).append((v[hull.vertices], unique_directions(hull.equations[:, :3]), unique_directions(edges)))
        moving = {n for n in self.meshes if n.startswith('arm_r_') or n == 'hand_r_base_link'}
        self.pairs = []
        for i, a in enumerate(sorted(self.meshes)):
            near = {a} | self.graph.get(a, set())
            near |= set().union(*(self.graph.get(b, set()) for b in tuple(near)))
            for b in sorted(self.meshes)[i + 1:]:
                if b not in near and ({a, b} & moving):
                    self.pairs.append((a, b))

    def collisions(self, q):
        frames = dict(self.frames)
        frames.update(self.k.forward(q, True))
        world = {name: [(v @ frames[name][:3, :3].T + frames[name][:3, 3],
                         n @ frames[name][:3, :3].T, e @ frames[name][:3, :3].T)
                        for v, n, e in meshes] for name, meshes in self.meshes.items()}
        found = []
        for a, b in self.pairs:
            for va, na, ea in world[a]:
                for vb, nb, eb in world[b]:
                    if np.any(va.max(0) < vb.min(0)) or np.any(vb.max(0) < va.min(0)):
                        continue
                    gap = maximum_gap(va, vb, np.vstack([na, nb]))
                    if gap >= -.0001:
                        continue
                    for begin in range(0, len(ea), 16):
                        axes = np.cross(ea[begin:begin + 16, None, :], eb[None, :, :]).reshape(-1, 3)
                        gap = max(gap, maximum_gap(va, vb, axes))
                        if gap >= -.0001:
                            break
                    if gap < -.0001:
                        found.append(dict(pair=[a, b], minimum_separating_axis_overlap_m=float(-gap)))
        return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trial', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stride', type=int, default=30)
    args = p.parse_args()
    assert args.stride > 0 and not args.output.exists()
    trace = np.load(args.trial / 'trace.npz')
    indices = sorted(set(range(0, len(trace['arm_q']), args.stride)) | {len(trace['arm_q']) - 1})
    checker = Clearance()
    rows = []
    for i in indices:
        pairs = checker.collisions(trace['arm_q'][i])
        if pairs:
            rows.append(dict(frame=i, time_s=float(trace['time'][i]), phase=str(trace['phase'][i]), collisions=pairs))
    result = dict(trial=args.trial.name, sampled_frames=len(indices), stride=args.stride,
        candidate_pairs=len(checker.pairs), collisions=rows, clear_at_samples=not rows,
        limitations='Convex exported geometry; two-edge joint/mount neighbours excluded; right finger self-contact excluded. Source physics self-collision remains disabled. Sampling is not continuous certification.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
