"""Previously verified carrying motor prefix; no physical state assignments."""
import json
from pathlib import Path
import numpy as np

class MotorReferencePreamble:
 def __init__(self,spec,output):
  self.start=float(spec['start_s']);self.end=float(spec['end_s']);self.motor=np.load(spec['path']);assert self.motor.shape[1]==27 and abs((self.end-self.start)*30-len(self.motor))<1e-6;self.anchor=None
  self.stream=(Path(output)/'motor-reference-preamble-call.jsonl').open('w',buffering=1)
 def active(self,t):
  frame=round(t*30);return round(self.start*30)<=frame<round(self.start*30)+len(self.motor)
 def command(self,t,issued):
  index=round((t-self.start)*30);assert 0<=index<len(self.motor),(index,t,self.start,self.end)
  if self.anchor is None:self.anchor=np.asarray(issued)-self.motor[0]
  target=self.motor[index]+self.anchor;self.stream.write(json.dumps(dict(time_s=t,index=index,anchor_max_rad=float(abs(self.anchor).max()),scope='Recorded MOTOR commands only; actualphysics uninterrupted, no recordedq/pose/velocity assignments'))+'\n');return target[:7],target[7:]
