"""Evaluation-only full-rate contact distribution. Normal contribution is not total axial force."""
import json
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_support_contact_measurement import PairForceMeter

class WrapContactMeter(PairForceMeter):
 def __init__(self,*args):
  super().__init__(*args);self.full_stream=(args[3]/'wrap-contact-physical-steps.jsonl').open('w');self.link_rows=[]
 def sample(self,t,states):
  super().sample(t,states)
  knife=next(i for i,n in self.names.items() if n=='link_0');rot=Rotation.from_quat(states[knife,3:7]).as_matrix();pairs=[]
  for c in self.gym.get_env_rigid_contacts(self.env):
   i,j=int(c['body0']),int(c['body1']);a,b=self.names.get(i,''),self.names.get(j,'')
   if a in ['link_0','link_1']:obj,hand,sgn,key=i,b,1,'localPos0'
   elif b in ['link_0','link_1']:obj,hand,sgn,key=j,a,-1,'localPos1'
   else:continue
   if not hand.startswith('hand_r_') or float(c['lambda'])<=1e-6:continue
   local=np.array([c[key][x] for x in ['x','y','z']]);world=Rotation.from_quat(states[obj,3:7]).apply(local)+states[obj,:3];pos=rot.T@(world-states[knife,:3]);normal=np.array([c['normal'][x] for x in ['x','y','z']]);f=sgn*float(c['lambda'])*rot.T@normal
   pairs.append(dict(hand_link=hand,knife_link=self.names[obj],position_knife_m=pos.tolist(),force_normal_contribution_knife_N=f.tolist(),normal_magnitude_N=float(c['lambda']),normal_moment_about_body_origin_Nm=np.cross(pos,f).tolist()))
  self.full_stream.write(json.dumps(dict(time_s=t,knife_world=states[knife].tolist(),contacts=pairs,axial_total_contact_force_N=None,axial_force_status='unavailable; normal projections only'))+'\n')
 def close(self):
  super().close();self.full_stream.close()
