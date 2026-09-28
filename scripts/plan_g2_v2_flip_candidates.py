"""At most four signed-axis G2 flip paths from an actual held state."""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_table_collision import ArmTableCollision
from scripts.g2_air_flip import plan_flip
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rise',type=float,default=.07);a=p.parse_args();a.output.mkdir(exist_ok=False)
 x=np.load(a.source/'trace.npz');k=G2Kinematics();check=ArmTableCollision(.75);w=transform(x['wrist'][-1,:3],x['wrist'][-1,3:]);o=transform(x['object'][-1,:3],x['object'][-1,3:]);q=x['reference_targets'][-1,:7];rows=[]
 for axis,angle in [('knife-length',180),('knife-length',-180),('wrist-forward',180),('wrist-forward',-180)]:
  path,d=plan_flip(k,w,o,q,angle,10,1/30,check,[0,0,a.rise],axis);rows.append(d);print(json.dumps(dict(axis=axis,angle=angle,feasible=d['feasible'],failure=d['failure'])),flush=True)
  if d['feasible']:break
 (a.output/'audit.json').write_text(json.dumps(dict(source=str(a.source),scope='CPU motor-only path planning from actual held knife/wrist; no cached scene reset',rows=rows),indent=2)+'\n')
if __name__=='__main__':main()
