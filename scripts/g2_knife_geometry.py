"""URDF collision geometry shared by measured-asset planner and diagnostics."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1]
BASELINE=ROOT/'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf'


class KnifeGeometry:
    def __init__(self,spec=None):
        self.spec=json.loads(Path(spec).read_text()) if spec else None
        self.urdf=ROOT/self.spec['asset_urdf'] if self.spec else BASELINE
        robot=ET.parse(self.urdf).getroot();joint=robot.find('joint')
        self.lower=float(joint.find('limit').get('lower'));self.upper=float(joint.find('limit').get('upper'))
        self.axis=np.fromstring(joint.find('axis').get('xyz'),sep=' ')
        origin=joint.find('origin');self.joint_xyz=np.fromstring(origin.get('xyz'),sep=' ')
        self.joint_r=Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix()
        self.parts=[]
        corners=np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]])
        for link in robot.findall('link'):
            for index,collision in enumerate(link.findall('collision')):
                geo=collision.find('geometry');mesh=geo.find('mesh');box=geo.find('box')
                if mesh is not None:
                    path=self.urdf.parent/mesh.get('filename');v=np.array([np.fromstring(line[2:],sep=' ') for line in path.read_text().splitlines() if line.startswith('v ')])
                    v*=np.fromstring(mesh.get('scale','1 1 1'),sep=' ')
                elif box is not None:v=corners*np.fromstring(box.get('size'),sep=' ')/2
                else:raise ValueError('Unsupported knife collision geometry')
                origin=collision.find('origin')
                if origin is not None:v=v@Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix().T+np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
                self.parts.append((link.get('name'),index,v))

    def collision_parts(self,slider=None):
        slider=self.lower if slider is None else slider;out=[]
        for name,index,points in self.parts:
            v=points.copy()
            if name=='link_1':v=v@self.joint_r.T+self.joint_xyz+self.joint_r@self.axis*slider
            hull=ConvexHull(v);out.append(dict(link=name,index=index,vertices=v[hull.vertices],normals=hull.equations[:,:3]))
        return out

    def table_pose(self,reference,table_z=.75,clearance=.0001):
        """Pre-first-step initial placement only, preserves supplied orientation."""
        out=reference.copy();v=np.concatenate([p['vertices'] for p in self.collision_parts()])
        out[2,3]=table_z-(v@out[:3,:3].T)[:,2].min()+clearance
        return out

    @property
    def side_half_width(self):
        return self.spec['planning']['side_half_width_m'] if self.spec else .0095

    @property
    def contact_y_interval(self):
        return self.spec['planning']['side_contact_y_interval_m'] if self.spec else [-.003,.002]
