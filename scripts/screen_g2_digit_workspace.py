"""Bounded geometric screening, explicitly not a physical support validation."""
import argparse, json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_seating_feedback import ContactCorrection
from scripts.wuji_kinematics import FINGERS


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--finger',choices=['ring','thumb'],required=True)
    a=p.parse_args();d=json.loads(a.source.read_text());c=ContactCorrection();w=c.w
    q=np.array(d['touch_q']);r=np.array(d['wrist_in_knife']);ns=np.array(d['contact_normals']);index=FINGERS.index(a.finger)
    ns[index]=[0,-1,0] if a.finger=='ring' else [-1,0,0]
    ids=[w.names.index('hand_r_'+a.finger+'_joint'+str(j)) for j in range(1,5)]
    targets=([[x,-.005,z] for z in [-.032,-.027,-.022,-.017,-.012] for x in [.003,.006,.009,.011]] if a.finger=='ring' else
             [[-.005,y,z] for z in [-.03205,-.02705,-.02205,-.01705,-.01205] for y in [.004,.0055,.007]])
    rows=[]
    for target in targets:
        def residual(v):
            proposed=q.copy();proposed[ids]=v
            return np.r_[(c.contacts(proposed,r,ns)[0][index]-target)*200,(v-q[ids])*.015]
        solved=least_squares(residual,q[ids],bounds=(w.lower[ids],w.upper[ids]),max_nfev=100,diff_step=1e-5)
        rows.append(dict(target=target,error_m=float(np.linalg.norm(residual(solved.x)[:3]/200)),q=solved.x.tolist()))
    if a.output.exists():raise ValueError('Choose a new output; preserve earlier geometry.')
    a.output.write_text(json.dumps(rows,indent=2)+'\n');print(str(a.output))


if __name__=='__main__':main()
