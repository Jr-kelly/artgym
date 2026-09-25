"""Index underside contact using distal motors only, from actual held geometry."""
import argparse
import json
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_seating_feedback import ContactCorrection
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous plan')
    d=json.loads(a.source.read_text());c=ContactCorrection();g=DigitGeometry(max_face_axes=32)
    q=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife']);normals=np.array(d['contact_normals']);normals[1]=[0,-1,0]
    def residual(v):
        proposed=q.copy();proposed[2:4]=v;point=c.contacts(proposed,relative,normals)[0][1]
        return np.r_[(point[1]+.003)*200,(point[0]-np.clip(point[0],-.007,.007))*200,
                     (point[2]-.035)*20,(v-q[2:4])*.01]
    result=least_squares(residual,np.clip(q[2:4],c.w.lower[2:4]+1e-7,c.w.upper[2:4]-1e-7),
        bounds=(c.w.lower[2:4],c.w.upper[2:4]),max_nfev=160,diff_step=1e-5)
    goal=q.copy();goal[2:4]=result.x;point=c.contacts(goal,relative,normals)[0][1];sweep=[]
    for alpha in np.linspace(0,1,21):
        proposed=q*(1-alpha)+goal*alpha
        sweep.append(dict(alpha=float(alpha),knife_gap_m=g.minimum_gap(proposed,relative,-.032674588,'index'),
            negative_self_pairs=[v for v in g.self_gaps(proposed,'index') if v['gap_lower_bound_m']<0]))
    geometry=dict(source=str(a.source),distal_q=result.x.tolist(),nominal_surface_point=point.tolist(),sweep=sweep,
        note='Root joint1/2 and all other motor targets remain unchanged. Target1mm inside underside is finite-drive preload, not a loaded physical state or measured force.')
    if abs(point[1]+.003)>=.001 or abs(point[0])>=.009:
        a.output.with_suffix('.rejected.json').write_text(json.dumps(geometry,indent=2)+'\n');raise ValueError('Distal-only contact geometry not reached')
    plan=json.loads(a.prefix.read_text());plan['stages']+=[
        dict(name='index_distal_establish',kind='move',moving_indices=[2,3],target=result.x.tolist(),seconds=2.),
        dict(name='index_distal_support_hold',kind='hold',seconds=1.,require_contacts=[1,2,3],require_no_contact=0,require_thumb_gap_m=.0041)]
    plan['new_distal_geometry']=geometry;a.output.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(dict(output=str(a.output),q=result.x.tolist(),point=point.tolist(),
        negative_pairs=sorted(set((r['moving_link'],r['other_link']) for s in sweep for r in s['negative_self_pairs'])))))


if __name__=='__main__':main()
