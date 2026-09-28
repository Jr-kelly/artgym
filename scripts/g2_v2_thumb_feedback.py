"""Explicit privileged geometric thumb baseline; controls robot motors only.
Actual object pose and slider q are oracle feedback, NOT student inputs.
Four supporting-finger references remain fixed. No force/slider drive calls.
"""
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_kinematics import WujiKinematics
class ThumbFeedback:
 def __init__(self,config,geometry,q,targets,wrist,obj,slider):
  self.c=config;self.fk=WujiKinematics();self.g=geometry;self.support=np.array(targets).copy();self.previous=np.array(targets).copy();self.anchor=np.array(config['anchor_local']);self.link=config['contact_link'];self.start=float(slider)-geometry.lower;self.last=dict()
  self.material_z=config['slider_material_z_m']
  if config.get('material_offset_at_takeover',False):
   f=np.linalg.inv(obj)@wrist@self.fk.forward(q)[self.link];point=f[:3,:3]@self.anchor+f[:3,3]
   self.material_z=float(point[2]-geometry.joint_xyz[2]-slider)
   assert abs(self.material_z)<geometry.spec['measured']['button_body_length_m']/2, 'Initial thumb material point outside button'
  self.initial_object=np.array(obj).copy()
  self.initialization=dict(material_z_m=self.material_z,actual_slider_m=float(slider),start_distance_m=self.start,source='one-time actual hand FK and simulation slider/body truth' if config.get('material_offset_at_takeover',False) else 'old contact material offset')
 def solve(self,q,wrist,obj,distance):
  if self.c.get('body_reference')=='fixed_takeover_world':obj=self.initial_object
  relative=np.linalg.inv(wrist)@obj;v=np.array([self.c['contact_x_m'],self.g.joint_xyz[1]+self.g.spec['geometry_hypothesis']['button_base_thickness_m']/2-self.c['normal_compression_m'],self.g.joint_xyz[2]+self.g.lower+distance+self.material_z]);target=relative[:3,:3]@v+relative[:3,3]
  fixed=np.array(q,dtype=float);normal=-relative[:3,1]
  def calculate(x):
   fixed[16:]=x;t=self.fk.forward(fixed)[self.link];return t[:3,:3]@self.anchor+t[:3,3],t[:3,0]
  old=self.previous[16:].copy()
  def residual(x):
   p,n=calculate(x);return np.r_[(p-target)*100,(n-normal)*self.c['normal_weight'],(x-old)*.01]
  fit=least_squares(residual,np.clip(old,self.fk.lower[16:]+1e-7,self.fk.upper[16:]-1e-7),bounds=(self.fk.lower[16:],self.fk.upper[16:]),max_nfev=30,diff_step=1e-5)
  point,_=calculate(fit.x);return fit.x,float(np.linalg.norm(point-target))
 def step(self,q,wrist,obj,slider,step):
  phase=step//150;u=min((step%150+1)/self.c['ramp_frames'],1.);u=10*u**3-15*u**4+6*u**5
  end=.04 if phase%2==0 else 0.;start=self.start if phase==0 else (0. if phase%2==0 else .04)
  reference=start+(end-start)*u
  correction=np.clip(self.c['slider_error_gain']*(reference-(float(slider)-self.g.lower)),-self.c['max_long_correction_m'],self.c['max_long_correction_m'])
  desired,error=self.solve(q,wrist,obj,reference+correction)
  command=self.support.copy();command[16:]=self.previous[16:]+np.clip(desired-self.previous[16:],-.025,.025);command=np.clip(command,self.fk.lower,self.fk.upper)
  self.last=dict(reference_distance_m=reference,long_feedback_m=float(correction),ik_error_m=error,desired_thumb=desired.tolist(),command_thumb=command[16:].tolist())
  self.previous=command.copy();return command
