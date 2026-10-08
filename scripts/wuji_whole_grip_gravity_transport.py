"""Coupled finite motor preload for changing object gravity during an arm turn.

Captured geometry/Jacobians only; no material-point tracking, pressure or native
contact feedback. The normal squeeze is not increased. This is not measured force.
"""
import json
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance

class WholeGripGravityTransport:
 def __init__(self,spec,output):
  self.s=spec;self.f=FunctionalEntryAffordance();self.kp=np.array(spec['hand_kp']);self.ready=False;self.log=(Path(output)/'whole-grip-gravity-transport.jsonl').open('w',buffering=1)
 def command(self,rotation,L,hand,issued,knife_rotation):
  if not self.ready:
   self.ready=True;self.base=issued.copy();self.base_force=knife_rotation.T@np.array([0,0,.055*9.81]);self.jacs=[];self.ids=[];P=[]
   for name,m in self.s['contact_material_points'].items():
    finger=name.split('_')[2];ids=np.array([self.f.g.w.names.index('hand_r_'+finger+'_joint'+str(j))for j in range(1,5)]);m=np.array(m);T=L@self.f.g.w.forward(hand)[name];P.append(T[:3,:3]@m+T[:3,3]);J=np.empty((3,4))
    for col,j in enumerate(ids):
     up=hand.copy().astype(float);down=hand.copy().astype(float);up[j]+=1e-5;down[j]-=1e-5;A=L@self.f.g.w.forward(up)[name];B=L@self.f.g.w.forward(down)[name];J[:,col]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
    self.jacs.append(J);self.ids.append(ids)
   com=np.array([0,.000113841678,-.012053567434]);self.A=np.zeros((6,2*len(P)))
   for i,point in enumerate(P):
    for j in range(2):
     F=np.eye(3)[j+1];self.A[:,2*i+j]=np.r_[F,np.cross(point-com,F)]
   scale=np.array([1,1,1,100,100,100]);self.solve=np.linalg.pinv(self.A*scale[:,None])*scale[None,:]
  desired_force=(rotation@knife_rotation).T@np.array([0,0,.055*9.81]);b=np.r_[desired_force-self.base_force,np.zeros(3)];forces=(self.solve@b).reshape(-1,2);residual=self.A@forces.reshape(-1)-b
  if np.linalg.norm(residual[:3])>1e-5:raise RuntimeError('Fixednormal tangenttransport cannotbalance thisrotation gravity')
  out=self.base.copy()
  for ids,J,dF in zip(self.ids,self.jacs,forces):out[ids]+=J.T@np.r_[0,dF]/self.kp[ids]
  margin=float(np.minimum(out-self.f.g.w.lower,self.f.g.w.upper-out).min())
  if margin<0:raise RuntimeError('Gravitytransport exceeds originalmotorlimits')
  self.log.write(json.dumps(dict(delta_tangent_knife_N=forces.tolist(),force_balance_residual_N=residual[:3].tolist(),moment_balance_residual_Nm=residual[3:].tolist(),issued_motor_delta_rad=(out-self.base).tolist(),minimum_motor_margin_rad=margin,scope=__doc__))+'\n');return out
