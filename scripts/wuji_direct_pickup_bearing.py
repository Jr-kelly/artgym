"""Track the newly acquired pinch while wrist lift changes contact geometry.

Own episode entry is captured once. Actual prior surface patches guide the
contact region; no native contact/force is consumed during control. Tangential
rolling is allowed, the arm never follows the body. Captured motor deformation
is added once, with a bounded gravity-bearing feedforward through current FK.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_direct_pickup import smooth


class DirectPickupBearing:
 def __init__(self,spec,output):
  self.s=spec;self.g=DigitGeometry(max_face_axes=8,knife_spec=Path(spec['knife_spec']));self.k=G2Kinematics();self.kp=np.array(spec['hand_kp']);self.kd=np.array(spec['hand_kd']);self.state=None;self.log=Path(output)/'direct-pickup-bearing.jsonl'
 def correct(self,t,O,arm,hand,issued,reference):
  if t<self.s['start_s']:return reference
  L=np.linalg.inv(O)@self.k.forward(arm);q=hand.astype(float);names=list(self.s['materials']);ids=np.r_[0:8,12:16];F=self.g.w.forward(q)
  def points(h):
   F=self.g.w.forward(h);out={}
   for n,material in self.s['materials'].items():
    T=L@F[n];out[n]=T[:3,:3]@np.asarray(material)+T[:3,3]
   return out,F
  if self.state is None:
   P,_=points(q);self.state=dict(source=q.copy(),points=P,deformation=issued-q,previous=q[ids].copy(),previous_time=t);self.initial_t=t
  state=self.state;targets={n:p.copy() for n,p in state['points'].items()};blend=smooth((t-self.initial_t)/.5);middle='hand_r_middle_pad_link';targets[middle][1]-=.003*blend
  previous=state['previous'];envelope=.02+.55*smooth((t-self.initial_t)/1.5);lo=np.maximum(self.g.w.lower[ids]+.035,np.maximum(previous-.06,state['source'][ids]-envelope));hi=np.minimum(self.g.w.upper[ids]-.035,np.minimum(previous+.06,state['source'][ids]+envelope))
  def residual(x):
   h=q.copy();h[ids]=x;P,F=points(h);r=[]
   for n in names:
    d=P[n]-targets[n];r.extend(d[:2]*500);r.append(d[2]*12);r.append(max(0.,abs(d[2])-.003)*700)
   for finger in ['index','middle','ring']:
    r.extend(min(0.,v['gap_lower_bound_m']-.0005)*700 for v in self.g.self_gaps(h,finger,certify_clearance_m=.0005,frames=F))
    for gap in self.g.gaps(h,L,0.,finger,frames=F):
     allowed=gap['hand_link'] in names and gap['knife_link']=='link_0';r.append(min(0.,gap['gap_lower_bound_m']-(-.00035 if allowed else .0002))*500)
   r.extend((x-state['source'][ids])*.035);return np.asarray(r)
  fit=least_squares(residual,np.clip(previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=25,diff_step=1e-5);h=q.copy();h[ids]=fit.x;P,F=points(h);cmd=reference.copy();logs={}
  for name,material in self.s['materials'].items():
   digit=name.split('_')[2];js=np.array([self.g.w.names.index('hand_r_'+digit+'_joint'+str(j)) for j in range(1,5)]);J=np.empty((3,4));mat=np.asarray(material)
   for j,index in enumerate(js):
    x=h.copy();x[index]+=1e-5;T=L@self.g.w.forward(x)[name];J[:,j]=(T[:3,:3]@mat+T[:3,3]-P[name])/1e-5
   deform=state['deformation'][js].copy()
   if digit=='middle':deform*=1-blend
   upward=float(self.s['world_up_reference_N'].get(digit,0.))*blend;force=O[:3,:3].T@np.array([0.,0.,upward]);offset=deform+np.clip(J.T@force/self.kp[js],-.1,.1)
   velocity=np.zeros(4)
   if t>state['previous_time']:
    old=q.copy();old[ids]=previous;velocity=(h[js]-old[js])/(t-state['previous_time'])
   lead=np.clip(self.kd[js]/self.kp[js]*velocity,-.05,.05);cmd[js]=np.clip(h[js]+offset+lead,self.g.w.lower[js]+.035,self.g.w.upper[js]-.035)
   logs[name]=dict(target_knife_m=targets[name].tolist(),planned_point_knife_m=P[name].tolist(),actual_point_knife_m=points(q)[0][name].tolist(),transverse_fit_m=float(np.linalg.norm(P[name][:2]-targets[name][:2])),world_up_reference_N=upward,captured_deformation_rad=deform.tolist(),planned_q=h[js].tolist(),command_q=cmd[js].tolist())
  if t==self.initial_t:cmd[ids]=issued[ids]
  state['previous']=fit.x.copy();state['previous_time']=t
  with self.log.open('a') as f:f.write(json.dumps(dict(elapsed_s=float(t),carriers=logs,scope=__doc__))+'\n')
  return cmd
