"""Runtime for development pickup policy; explicit simulation pose input."""
import numpy as np,torch
from scripts.train_wuji_flat_pickup import PickupActor
class FlatPickupPolicy:
 def __init__(self,checkpoint):
  self.saved=torch.load(checkpoint,map_location='cpu');self.model=PickupActor();self.model.load_state_dict(self.saved['model']);self.model.eval();self.span=np.array(self.saved['config']['motor_span']);self.slew=np.array(self.saved['config']['motor_slew']);self.offset=np.zeros(27);self.last=np.zeros(27);self.age=0;self.records=[]
 def command(self,q,vel,issued,relative,reference):
  obs=np.r_[q,issued-q,vel*.05,relative[:3]*10,relative[3:7],self.age/181,self.offset]
  if self.age%5==0:
   with torch.no_grad():self.last=self.model.actor(torch.tensor(obs,dtype=torch.float32)).numpy().clip(-1,1)
  self.offset+=np.clip(self.last*self.span-self.offset,-self.slew,self.slew);self.records.append(dict(age=self.age,pose_source='sim_oracle30Hz',offset=self.offset.tolist()));self.age+=1;return reference+self.offset
