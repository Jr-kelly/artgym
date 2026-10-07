"""Whole-digit collision-hull separation from both knife links (metres).

Positive SAT gaps are conservative lower bounds on Euclidean clearance.
Negative values fail this separation certificate and require an intersection
check; they are not a calibrated penetration depth.
Uses collision geometry, measured joint positions and measured wrist/object pose.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics,ROOT

class DigitGeometry:
    def __init__(self,max_face_axes=None,knife_spec=None):
        self.w=WujiKinematics();self.meshes={}
        self.knife_geometry=None
        if knife_spec is not None:
            from scripts.g2_knife_geometry import KnifeGeometry
            self.knife_geometry=KnifeGeometry(knife_spec)
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

    def gaps(self,q,wrist_in_object,slider,finger='thumb',frames=None,knife_parts=None,certify_clearance_m=None):
        frames=self.w.forward(q) if frames is None else frames;results=[]
        if self.knife_geometry is not None:
            for link,meshes in self.meshes.items():
                if '_'+finger+'_' not in link:continue
                frame=wrist_in_object@frames[link]
                for vertices,normals in meshes:
                    v=vertices@frame[:3,:3].T+frame[:3,3]
                    for part in (self.knife_geometry.collision_parts(slider) if knife_parts is None else knife_parts):
                        if certify_clearance_m is not None:
                            # Knife face planes give an inexpensive exact
                            # positive certificate for distant hand parts.
                            # Failed certificates still use every hand face.
                            probe=part['normals'];a=v@probe.T;b=part['vertices']@probe.T
                            face_gap=float(np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0)).max())
                            if face_gap>certify_clearance_m:
                                results.append(dict(hand_link=link,knife_link=part['link'],knife_component=part['index'],gap_lower_bound_m=face_gap,certificate='knife face planes'))
                                continue
                        axes=np.r_[normals@frame[:3,:3].T,part['normals']];a=v@axes.T;b=part['vertices']@axes.T
                        gap=np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0)).max()
                        results.append(dict(hand_link=link,knife_link=part['link'],knife_component=part['index'],gap_lower_bound_m=float(gap)))
            return results
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

    def self_gaps(self,q,finger,certify_clearance_m=None,frames=None,transformed=None,enclosing_spheres=None,pair_clearances=None):
        """Conservative face-axis gaps to other digits; exclude shared palm.

        Positive certifies separation. Negative requires an exact convex
        intersection check before calling it an intersection.
        """
        frames=self.w.forward(q) if frames is None else frames
        if transformed is None:
            transformed={}
            for name,meshes in self.meshes.items():
                if not any('_'+f+'_' in name for f in ['thumb','index','middle','ring','pinky']):continue
                frame=frames[name]
                transformed[name]=[(v@frame[:3,:3].T+frame[:3,3],n@frame[:3,:3].T) for v,n in meshes]
        result=[]
        for a,ma in transformed.items():
            if '_'+finger+'_' not in a:continue
            for b,mb in transformed.items():
                if '_'+finger+'_' in b:continue
                for ia,(va,na) in enumerate(ma):
                    for ib,(vb,nb) in enumerate(mb):
                        if certify_clearance_m is not None:
                            if enclosing_spheres is None:
                                ca,cb=va.mean(0),vb.mean(0)
                                ra,rb=np.linalg.norm(va-ca,axis=1).max(),np.linalg.norm(vb-cb,axis=1).max()
                            else:
                                ca,ra=enclosing_spheres[a,ia];cb,rb=enclosing_spheres[b,ib]
                            sphere=float(np.linalg.norm(ca-cb)-ra-rb)
                            required_clearance=(pair_clearances or {}).get(tuple(sorted((a,b))),certify_clearance_m)
                            if sphere>required_clearance:
                                # Enclosing spheres certify Euclidean separation;
                                # all potentially close pairs retain full face SAT.
                                result.append(dict(moving_link=a,other_link=b,gap_lower_bound_m=sphere,certificate='enclosing spheres'))
                                continue
                        axes=np.r_[na,nb];pa=va@axes.T;pb=vb@axes.T
                        gap=np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()
                        result.append(dict(moving_link=a,other_link=b,gap_lower_bound_m=float(gap)))
        return result

    def pair_gaps(self,q,pairs,certify_clearance_m=None):
        """Conservative face-axis separation for explicitly named own/palm pairs."""
        frames=self.w.forward(q);results=[];parts={}
        for name in {name for pair in pairs for name in pair}:
            frame=frames[name]
            parts[name]=[(v@frame[:3,:3].T+frame[:3,3],n@frame[:3,:3].T)
                         for v,n in self.meshes[name]]
        for a,b in pairs:
            for va,na in parts[a]:
                for vb,nb in parts[b]:
                    if certify_clearance_m is not None:
                        # A positive world-axis gap certifies separation.
                        # Near pairs retain every original face axis; this
                        # only avoids expensive projections for distant pairs.
                        box_gap=float(np.maximum(va.min(0)-vb.max(0),vb.min(0)-va.max(0)).max())
                        if box_gap>certify_clearance_m:
                            results.append(dict(link_a=a,link_b=b,gap_lower_bound_m=box_gap,certificate='world axes'))
                            continue
                        # Any original face plane can certify separation. Try
                        # a small subset before projecting every curved hull
                        # face; if it cannot certify the requested clearance,
                        # retain the complete original calculation below.
                        sa=na[np.linspace(0,len(na)-1,min(12,len(na)),dtype=int)]
                        sb=nb[np.linspace(0,len(nb)-1,min(12,len(nb)),dtype=int)]
                        probe=np.r_[sa,sb];pa=va@probe.T;pb=vb@probe.T
                        face_gap=float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
                        if face_gap>certify_clearance_m:
                            results.append(dict(link_a=a,link_b=b,gap_lower_bound_m=face_gap,certificate='original face subset'))
                            continue
                    axes=np.r_[na,nb];pa=va@axes.T;pb=vb@axes.T
                    gap=np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()
                    results.append(dict(link_a=a,link_b=b,gap_lower_bound_m=float(gap)))
        return results
