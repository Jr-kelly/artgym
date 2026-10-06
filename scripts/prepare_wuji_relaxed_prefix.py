"""Park inactive digits with measured clearance; retain functional motor paths."""
import argparse,json,copy
from pathlib import Path
import numpy as np
def smooth(x):
    x=np.clip(x,0,1)
    return x*x*x*(10-15*x+6*x*x)

def prepare(source,output,duration=76):
    p=json.loads(source.read_text());old=copy.deepcopy(p)
    park=np.array([.6,0.,.9,.4]);thumb=np.array([.8,.3,.7,.1])
    for r in p['rows']:
        t=r['time_s'];q=np.array(r['hand_q'])
        if t<18:
            u=smooth((t-12)/6)
            q[4:8]=(1-u)*park+u*q[4:8]
            q[16:20]=(1-u)*thumb+u*q[16:20]
        if t<70:
            u=smooth((t-66)/4)
            q[8:12]=(1-u)*park+u*q[8:12]
            q[12:16]=(1-u)*park+u*q[12:16]
        r['hand_q']=q.tolist()
    p['rows']=[r for r in p['rows'] if r['time_s']<=duration]
    p['duration_s']=duration
    p['action_quality_change']=dict(source=str(source),parked_nonfunctional_digits_rad=park.tolist(),early_thumb_rad=thumb.tolist(),preserved='index table-push, active index/middle/thumb grasp/transport/release and B',reason='Initial unused thumb/middle convex intersection and later unnecessary ring/pinky folding; no model/drive/contact changes')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(p));return p

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=float,default=76);a=p.parse_args();prepare(a.source,a.output,a.duration)
