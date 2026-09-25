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
    def __init__(self,max_face_axes=None):
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
                hull=ConvexHull(v);normals=hull.equations[:,:3]
                if max_face_axes is not None and len(normals)>max_face_axes:
                    # Planning only: fewer separating axes keep positive gaps
                    # conservative because every original vertex is retained.
                    # Runtime diagnostics use the default full set.
                    normals=normals[np.linspace(0,len(normals)-1,max_face_axes,dtype=int)]
                self.meshes.setdefault(name,[]).append((v[hull.vertices],normals))

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

    def self_gaps(self,q,finger):
        """Conservative face-axis gaps to other digits; exclude shared palm.

        Positive certifies separation. Negative requires an exact convex
        intersection check before calling it an intersection.
        """
        frames=self.w.forward(q);transformed={}
        for name,meshes in self.meshes.items():
            if not any('_'+f+'_' in name for f in ['thumb','index','middle','ring','pinky']):continue
            frame=frames[name]
            transformed[name]=[(v@frame[:3,:3].T+frame[:3,3],n@frame[:3,:3].T) for v,n in meshes]
        result=[]
        for a,ma in transformed.items():
            if '_'+finger+'_' not in a:continue
            for b,mb in transformed.items():
                if '_'+finger+'_' in b:continue
                for va,na in ma:
                    for vb,nb in mb:
                        axes=np.r_[na,nb];pa=va@axes.T;pb=vb@axes.T
                        gap=np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()
                        result.append(dict(moving_link=a,other_link=b,gap_lower_bound_m=float(gap)))
        return result

    def pair_gaps(self,q,pairs):
        """Conservative face-axis separation for explicitly named own/palm pairs."""
        frames=self.w.forward(q);results=[]
        for a,b in pairs:
            fa,fb=frames[a],frames[b]
            for va,na in self.meshes[a]:
                va=va@fa[:3,:3].T+fa[:3,3];na=na@fa[:3,:3].T
                for vb,nb in self.meshes[b]:
                    vb=vb@fb[:3,:3].T+fb[:3,3];nb=nb@fb[:3,:3].T
                    axes=np.r_[na,nb];pa=va@axes.T;pb=vb@axes.T
                    gap=np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()
                    results.append(dict(link_a=a,link_b=b,gap_lower_bound_m=float(gap)))
        return results
