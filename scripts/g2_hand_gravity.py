"""URDF hand gravity feedforward through position targets only.

No simulator handle, force API or object inputs. Torques are MODEL values,
not sensor measurements. Arm/base gravity is handled by the existing G2 servo.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics


class HandGravity:
    def __init__(self, stiffness):
        self.arm=G2Kinematics();self.hand=WujiKinematics()
        self.stiffness=np.asarray(stiffness,dtype=float)
        assert self.stiffness.shape==(20,) and np.all(self.stiffness>0)
        self.parents={'hand_r_base_link':[]};self.axes={}
        for parent,child,origin,index,axis in self.hand.joints:
            self.parents[child]=self.parents[parent]+([] if index is None else [index])
            if index is not None:self.axes[index]=(child,axis)
        urdf=Path(__file__).resolve().parents[1]/'assets/robots/g2_wuji/g2_wuji.urdf'
        self.masses={}
        for link in ET.parse(urdf).getroot().findall('link'):
            inertial=link.find('inertial');name=link.get('name')
            if name not in self.parents or inertial is None:continue
            origin=inertial.find('origin')
            com=np.fromstring(origin.get('xyz','0 0 0'),sep=' ') if origin is not None else np.zeros(3)
            self.masses[name]=(float(inertial.find('mass').get('value')),com)

    def torque(self, robot_q):
        q=np.asarray(robot_q,dtype=float);assert q.shape==(27,)
        frames=self.hand.forward(q[7:27]);wrist=self.arm.forward(q[:7])
        gravity=wrist[:3,:3].T@np.array([0.,0.,-9.81]);result=np.zeros(20)
        axes={i:(frames[name][:3,:3]@axis,frames[name][:3,3]) for i,(name,axis) in self.axes.items()}
        for name,(mass,center) in self.masses.items():
            frame=frames[name];point=frame[:3,:3]@center+frame[:3,3]
            for index in self.parents[name]:
                axis,origin=axes[index]
                result[index]-=mass*np.dot(gravity,np.cross(axis,point-origin))
        return result

    def bias(self, robot_q):
        torque=self.torque(robot_q)
        return np.clip(torque/self.stiffness,-.08,.08),torque
