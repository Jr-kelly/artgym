"""Change only closed motor targets while preserving an existing pickup geometry."""
import argparse,copy,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scripts.g2_seating_feedback import ContactCorrection

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--squeeze',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    initial=json.loads(a.input.read_text());c=ContactCorrection();w=c.w;q0=np.array(initial['touch_q'])
    wrist=np.array(initial['wrist_in_knife']);normals=np.array([[1,0,0]]+[[-1,0,0]]*4)
    mesh={}
    for n in w.forward(q0):
        file=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')
        v=np.array([np.fromstring(l[2:],sep=' ') for l in file.read_text().splitlines() if l.startswith('v ')]);mesh[n]=v[ConvexHull(v).vertices]
    def solve(squeeze):
        desired=np.array(initial['contact_targets'])-normals*squeeze
        def residual(q):
            pts=c.contacts(q,wrist,normals)[0];vv=[]
            for n,t in w.forward(q).items():
                t=wrist@t;vv.append(mesh[n]@t[:3,:3].T+t[:3,3])
            v=np.concatenate(vv)
            return np.r_[(pts-desired).ravel()*200,np.minimum(v[:,1]+.003,0)*90,(q-q0)*.5]
        result=least_squares(residual,q0,bounds=(np.maximum(w.lower,q0-.5),np.minimum(w.upper,q0+.5)),max_nfev=100,diff_step=1e-5)
        return result.x,float(result.cost)
    baseline,cost0=solve(initial['squeeze_m']);changed,cost1=solve(a.squeeze)
    command=np.clip(np.array(initial['close_q'])+changed-baseline,w.lower,w.upper)
    out=copy.deepcopy(initial);out.update(close_q=command.tolist(),squeeze_m=a.squeeze,
        pressure_retarget=dict(source=str(a.input),baseline_squeeze_m=initial['squeeze_m'],baseline_cost=cost0,new_cost=cost1,
            max_target_change_rad=float(np.max(abs(command-initial['close_q']))),
            method='Closed-command delta between two fixed-wrist optimizations; original wrist, touch, and open states are identical.'))
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['pressure_retarget']))

if __name__=='__main__':main()
