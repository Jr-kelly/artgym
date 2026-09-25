"""Add one opposing little-finger side contact to an actual held knife.

Preflight distinguishes the unloaded touch pose from a finite-drive1mm closing
command. It does not interpret command penetration as physical penetration or
as measured force. All other motor targets remain fixed.
"""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_seating_feedback import ContactCorrection


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous result')
    d=json.loads(a.source.read_text());g=DigitGeometry(max_face_axes=32);full=DigitGeometry();c=ContactCorrection();w=g.w
    q=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife']);normals=np.array([[1,0,0]]*5);point=c.contacts(q,relative,normals)[0][4]
    target=point.copy();target[:2]=[.00965,0];target[2]=np.clip(point[2],-.055,-.025)
    def surface(v):
        qs=q.copy();qs[8:12]=v;return qs,c.contacts(qs,relative,normals)[0][4]
    def solve(target,seed,command=False):
        def residual(v):
            qs,pt=surface(v)
            return np.r_[(pt-target)*300,[min(s['gap_lower_bound_m']-( -.0011 if command else .00005),0)*600 for s in g.gaps(qs,relative,-.032674588,'pinky')],
                [min(s['gap_lower_bound_m']-.00015,0)*500 for s in g.self_gaps(qs,'pinky')],(v-seed)*.005]
        return least_squares(residual,np.clip(seed,w.lower[8:12]+1e-7,w.upper[8:12]-1e-7),bounds=(w.lower[8:12],w.upper[8:12]),max_nfev=150,diff_step=1e-5)
    touch=solve(target,q[8:12]);touchq,actual_point=surface(touch.x);goal=target.copy();goal[0]=.0085;command=solve(goal,touch.x,True)
    sweep=[]
    for alpha in np.linspace(0,1,31):
        test=q*(1-alpha)+touchq*alpha;selfgap=min(v['gap_lower_bound_m'] for v in full.self_gaps(test,'pinky'))
        sweep.append(dict(alpha=float(alpha),knife_gap_m=full.minimum_gap(test,relative,-.032674588,'pinky'),self_gap_m=selfgap))
    valid=bool(np.linalg.norm(actual_point-target)<.001 and min(v['knife_gap_m'] for v in sweep)>=-.00015 and min(v['self_gap_m'] for v in sweep)>=0)
    close_sweep=[]
    for alpha in np.linspace(0,1,21):
        test=touchq.copy();test[8:12]=touch.x*(1-alpha)+command.x*alpha
        close_sweep.append(dict(alpha=float(alpha),nominal_knife_gap_m=full.minimum_gap(test,relative,-.032674588,'pinky'),
            self_gap_m=min(v['gap_lower_bound_m'] for v in full.self_gaps(test,'pinky'))))
    valid=valid and min(v['self_gap_m'] for v in close_sweep)>=0 and min(v['nominal_knife_gap_m'] for v in close_sweep)>=-.0012
    geometry=dict(source=str(a.source),target_point=target.tolist(),touch_point=actual_point.tolist(),touch_q=touch.x.tolist(),command_q=command.x.tolist(),
        close_target_point=goal.tolist(),close_actual_nominal_point=surface(command.x)[1].tolist(),sweep=sweep,closing_command_sweep=close_sweep,geometric_preflight=valid,
        scope='One-finger side support opposite existing left-bottom contacts; touch first, then1mm finite-drive preload. No force estimate.')
    plan=json.loads(a.prefix.read_text());plan['pinky_support_geometry']=geometry
    plan['stages'] += [dict(name='pinky_side_touch',kind='move',moving_indices=list(range(8,12)),target=touch.x.tolist(),seconds=2.,require_thumb_gap_m=.0041),
        dict(name='pinky_side_close',kind='move',moving_indices=list(range(8,12)),target=command.x.tolist(),seconds=1.,require_thumb_gap_m=.0041),
        dict(name='pinky_four_support_hold',kind='hold',seconds=1.,require_contacts=[1,2,3,4],require_no_contact=0,require_thumb_gap_m=.0041)]
    path=a.output if valid else a.output.with_suffix('.rejected.json');path.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(dict(output=str(path),valid=valid,target=target.tolist(),point=actual_point.tolist(),min_knife_gap_m=min(v['knife_gap_m'] for v in sweep),min_self_gap_m=min(v['self_gap_m'] for v in sweep))))


if __name__=='__main__':main()
