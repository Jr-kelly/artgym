"""Whole-digit collision-hull separation from both knife links (metres).

Positive SAT gaps are conservative lower bounds on Euclidean clearance.
Negative values indicate convex overlap, not a calibrated penetration depth.
Uses collision geometry, measured joint positions and measured wrist/object pose.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics,ROOT

class DigitGeometry:
    def __init__(self):
        self.w=WujiKinematics();self.meshes={}
        path=ROOT/'assets/hands/wuji_artbot/right.urdf';xml=ET.parse(path).getroot()
        for link in xml.findall('link'):
            name=link.get('name')
            for collision in link.findall('collision'):
                mesh=collision.find('geometry/mesh')
                if mesh is None:continue
                file=path.parent/mesh.get('filename');v=np.array([np.fromstring(s[2:],sep=' ') for s in file.read_text().splitlines() if s.startswith('v ')])
                v*=np.fromstring(mesh.get('scale','1 1 1'),sep=' ')
                origin=collision.find('origin')
                if origin is not None:
                    v=v@Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix().T+np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
                hull=ConvexHull(v);self.meshes.setdefault(name,[]).append((v[hull.vertices],hull.equations[:,:3]))

    def gaps(self,q,wrist_in_object,slider,finger='thumb'):
        frames=self.w.forward(q);results=[]
        boxes=[('link_0',np.zeros(3),np.array([.019,.008,.147])/2),
               ('link_1',np.array([0,.0055,.010624586881962734+slider]),np.array([.01,.003,.03])/2)]
        for link,meshes in self.meshes.items():
            if '_'+finger+'_' not in link:continue
            frame=wrist_in_object@frames[link]
            for vertices,normals in meshes:
                v=vertices@frame[:3,:3].T+frame[:3,3];axes=np.r_[np.eye(3),normals@frame[:3,:3].T]
                axes/=np.linalg.norm(axes,axis=1)[:,None]
                for body,center,half in boxes:
                    lower=center@axes.T-abs(axes)@half;upper=center@axes.T+abs(axes)@half
                    proj=v@axes.T;gap=np.maximum(proj.min(0)-upper,lower-proj.max(0))
                    # Face axes suffice to certify positive separation. If no
                    # separation is found, conservatively do not certify clearance.
                    results.append(dict(hand_link=link,knife_link=body,gap_lower_bound_m=float(gap.max())))
        return results

    def minimum_gap(self,q,wrist_in_object,slider,finger='thumb'):
        return min(v['gap_lower_bound_m'] for v in self.gaps(q,wrist_in_object,slider,finger))
