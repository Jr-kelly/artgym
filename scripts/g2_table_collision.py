"""Convex G2 arm/palm versus the actual tabletop box, for IK path screening.

Uses the exported collision meshes and the separating-axis theorem, including
edge cross products. Finger contacts are checked in the physical runner; closed
motor targets are not assumed to be attainable finger configurations.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics, ROOT


class ArmTableCollision:
    def __init__(self, table_height=.8, margin=.002):
        self.k = G2Kinematics()
        self.center = np.array([.60, -.25, table_height-.025])
        self.half = np.array([.30, .40, .025]) + margin
        path = ROOT/'assets/robots/g2_wuji/g2_wuji.urdf'
        self.meshes = []
        names = set(self.k.forward(np.zeros(7), True))
        for link in ET.parse(path).getroot().findall('link'):
            name = link.get('name')
            if name not in names:
                continue
            for collision in link.findall('collision'):
                mesh = collision.find('geometry/mesh')
                if mesh is None:
                    raise ValueError('Unsupported collision geometry: '+name)
                v = np.array([np.fromstring(line[2:], sep=' ') for line in
                              (path.parent/mesh.get('filename')).read_text().splitlines() if line.startswith('v ')])
                v *= np.fromstring(mesh.get('scale', '1 1 1'), sep=' ')
                origin = collision.find('origin')
                if origin is not None:
                    r = Rotation.from_euler('xyz', np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')).as_matrix()
                    v = v@r.T + np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
                hull = ConvexHull(v)
                edges = np.concatenate([v[hull.simplices[:, a]]-v[hull.simplices[:, b]] for a,b in [(0,1),(1,2),(2,0)]])
                self.meshes.append((name, v[hull.vertices], hull.equations[:, :3], edges))

    def collisions(self, q):
        frames = self.k.forward(q, True)
        collisions = []
        for name, vertices, normals, edges in self.meshes:
            t = frames[name]
            v = vertices@t[:3,:3].T + t[:3,3]
            if np.any(v.max(0)<self.center-self.half) or np.any(v.min(0)>self.center+self.half):
                continue
            axes = np.concatenate([np.eye(3), normals@t[:3,:3].T] +
                                  [np.cross(edges@t[:3,:3].T, axis) for axis in np.eye(3)])
            norm = np.linalg.norm(axes, axis=1)
            axes = axes[norm>1e-9]/norm[norm>1e-9,None]
            projection = (v-self.center)@axes.T
            radius = np.abs(axes)@self.half
            gap = np.maximum(projection.min(0)-radius, -radius-projection.max(0))
            if gap.max()<=0:
                collisions.append(dict(link=name, separating_axis_overlap_m=float(-gap.max())))
        return collisions
