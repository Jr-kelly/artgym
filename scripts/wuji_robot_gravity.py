"""URDF gravity feedforward for planning initialization before native FK updates."""
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

class RobotGravity:
 def __init__(self,path='assets/robots/g2_wuji/g2_wuji.urdf',names=None):
  r=ET.parse(path).getroot();self.names=names;self.joints=[];self.links=[]
  for j in r.findall('joint'):
   o=j.find('origin');T=np.eye(4)
   if o is not None:
    T[:3,3]=np.fromstring(o.get('xyz','0 0 0'),sep=' ');T[:3,:3]=Rotation.from_euler('xyz',np.fromstring(o.get('rpy','0 0 0'),sep=' ')).as_matrix()
   ax=j.find('axis');self.joints.append((j.find('parent').get('link'),j.find('child').get('link'),T,self.names.index(j.get('name')) if j.get('name') in self.names else None,np.fromstring(ax.get('xyz'),sep=' ') if ax is not None else None))
  children={j[1] for j in self.joints};self.root=next(l.get('name') for l in r.findall('link') if l.get('name') not in children)
  for l in r.findall('link'):
   i=l.find('inertial')
   if i is not None:
    o=i.find('origin');self.links.append((l.get('name'),float(i.find('mass').get('value')),np.fromstring(o.get('xyz','0 0 0'),sep=' ') if o is not None else np.zeros(3)))
 def potential(self,q):
  frames={self.root:np.eye(4)};pending=list(self.joints)
  while pending:
   for row in list(pending):
    parent,child,T,idx,axis=row
    if parent not in frames:continue
    A=T.copy()
    if idx is not None:A[:3,:3]=T[:3,:3]@Rotation.from_rotvec(axis*q[idx]).as_matrix()
    frames[child]=frames[parent]@A;pending.remove(row)
  return 9.81*sum(m*(frames[n][:3,:3]@com+frames[n][:3,3])[2] for n,m,com in self.links)
 def __call__(self,q):
  q=np.asarray(q,dtype=float);out=np.zeros(len(q));eps=1e-5
  for i in range(len(q)):
   a=q.copy();b=q.copy();a[i]+=eps;b[i]-=eps;out[i]=(self.potential(a)-self.potential(b))/(2*eps)
  return out
