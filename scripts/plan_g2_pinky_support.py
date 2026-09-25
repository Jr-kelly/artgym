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
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--finger',choices=['pinky','index'],default='pinky');p.add_argument('--retained-supports',type=int,nargs='+',help='Contact indices in thumb/index/middle/ring/pinky order retained at each new hold.')
    p.add_argument('--ik-seed',choices=['actual','functional'],default='actual',help='One explicit alternative IK branch; only a planning seed, never an initial physical state.')
    p.add_argument('--surface',choices=['side','underside'],default='side');p.add_argument('--contact-z',type=float);p.add_argument('--contact-x',type=float,default=-.005,help='Declared underside transverse point in knife coordinates.')
    p.add_argument('--held-thumb',action='store_true',help='Candidate2 support is thumb/middle/ring; do not impose the original route thumb-release gate.')
    p.add_argument('--approach-under',action='store_true',help='For underside contact, first reach a point12mm below the touch point, hold, then approach; preserves failed direct interpolation as a separate proposal.')
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous result')
    d=json.loads(a.source.read_text());g=DigitGeometry(max_face_axes=32);full=DigitGeometry();c=ContactCorrection();w=g.w
    slider=float(np.load(d['source_trace'])['slider'][d['source_step']])
    q=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife']);normals=np.array([[1,0,0]]*5)
    contact_id=4 if a.finger=='pinky' else 1;indices=np.arange(8,12) if a.finger=='pinky' else np.arange(4)
    if a.surface=='underside':normals[contact_id]=[0,-1,0]
    point=c.contacts(q,relative,normals)[0][contact_id]
    target=point.copy();target[:2]=[.00965,0] if a.surface=='side' else [a.contact_x,-.00415]
    target[2]=a.contact_z if a.contact_z is not None else np.clip(point[2],-.055,-.025)
    def surface(v):
        qs=q.copy();qs[indices]=v;return qs,c.contacts(qs,relative,normals)[0][contact_id]
    if a.approach_under and a.surface!='underside':raise ValueError('Under-body approach requires underside surface')
    def solve(target,seed,command=False,free=False):
        def residual(v):
            qs,pt=surface(v)
            return np.r_[(pt-target)*300,[min(s['gap_lower_bound_m']-(-.0011 if command else (.0048 if free else .00005)),0)*600 for s in g.gaps(qs,relative,slider,a.finger)],
                [min(s['gap_lower_bound_m']-.00015,0)*500 for s in g.self_gaps(qs,a.finger)],(v-seed)*.005]
        return least_squares(residual,np.clip(seed,w.lower[indices]+1e-7,w.upper[indices]-1e-7),bounds=(w.lower[indices],w.upper[indices]),max_nfev=150,diff_step=1e-5)
    pre=None;preq=None;prepoint=None;seed=q[indices]
    if a.ik_seed=='functional':seed=np.load(Path(__file__).resolve().parents[1]/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0][indices]
    if a.approach_under:
        prepoint=target.copy();prepoint[1]-=.012;pre=solve(prepoint,seed,free=True);preq=surface(pre.x)[0]
    touch=solve(target,pre.x if pre is not None else seed);touchq,actual_point=surface(touch.x);goal=target.copy()
    if a.surface=='side':goal[0]=.0085
    else:goal[1]=-.003
    command=solve(goal,touch.x,True)
    sweep=[]
    pieces=[(q,touchq)] if preq is None else [(q,preq),(preq,touchq)]
    for piece,(begin,end) in enumerate(pieces):
        for alpha in np.linspace(0,1,31):
            test=begin*(1-alpha)+end*alpha;selfgap=min(v['gap_lower_bound_m'] for v in full.self_gaps(test,a.finger))
            sweep.append(dict(segment=piece,alpha=float(alpha),knife_gap_m=full.minimum_gap(test,relative,slider,a.finger),self_gap_m=selfgap))
    valid=bool(np.linalg.norm(actual_point-target)<.001 and min(v['knife_gap_m'] for v in sweep)>=-.00015 and min(v['self_gap_m'] for v in sweep)>=0)
    if preq is not None:valid=valid and full.minimum_gap(preq,relative,slider,a.finger)>=.0041 and np.linalg.norm(surface(pre.x)[1]-prepoint)<.001
    close_sweep=[]
    for alpha in np.linspace(0,1,21):
        test=touchq.copy();test[indices]=touch.x*(1-alpha)+command.x*alpha
        close_sweep.append(dict(alpha=float(alpha),nominal_knife_gap_m=full.minimum_gap(test,relative,slider,a.finger),
            self_gap_m=min(v['gap_lower_bound_m'] for v in full.self_gaps(test,a.finger))))
    valid=valid and min(v['self_gap_m'] for v in close_sweep)>=0 and min(v['nominal_knife_gap_m'] for v in close_sweep)>=-.0012
    geometry=dict(source=str(a.source),target_point=target.tolist(),touch_point=actual_point.tolist(),touch_q=touch.x.tolist(),command_q=command.x.tolist(),
        close_target_point=goal.tolist(),close_actual_nominal_point=surface(command.x)[1].tolist(),sweep=sweep,closing_command_sweep=close_sweep,geometric_preflight=valid,
        contact_surface=a.surface,held_thumb=a.held_thumb,
        approach_under=a.approach_under,pre_q=None if preq is None else pre.x.tolist(),pre_point=None if prepoint is None else prepoint.tolist(),
        scope='One-finger support; touch first, then1mm finite-drive preload. No force estimate. Held-thumb option retains actual candidate2 opposed grip; original option keeps thumb released.')
    plan=json.loads(a.prefix.read_text());plan['pinky_support_geometry']=geometry
    stages=[]
    if preq is not None:
        stages += [dict(name='pinky_under_clearance',kind='move',moving_indices=indices.tolist(),target=pre.x.tolist(),seconds=max(2.,1.875*np.max(abs(pre.x-q[indices]))),require_thumb_gap_m=.0041),
            dict(name='pinky_under_clear_hold',kind='hold',seconds=1.,require_contacts=[0,2,3] if a.held_thumb else [1,2,3],require_no_contact=contact_id,require_thumb_gap_m=.0041)]
    stages += [dict(name='pinky_side_touch',kind='move',moving_indices=indices.tolist(),target=touch.x.tolist(),seconds=2.,require_thumb_gap_m=.0041),
        dict(name='pinky_side_close',kind='move',moving_indices=indices.tolist(),target=command.x.tolist(),seconds=1.,require_thumb_gap_m=.0041),
        dict(name='pinky_four_support_hold',kind='hold',seconds=1.,require_contacts=[1,2,3,4],require_no_contact=0,require_thumb_gap_m=.0041)]
    if a.held_thumb:
        for stage in stages:
            stage.pop('require_thumb_gap_m',None)
            if stage.get('require_no_contact')==0:stage.pop('require_no_contact')
            stage['name']=stage['name'].replace('side',a.surface)
        stages[-1]['require_contacts']=[0,2,3,4]
    if a.retained_supports:
        for stage in stages:
            if stage['kind']=='hold':stage['require_contacts']=list(a.retained_supports)
        stages[-1]['require_contacts']=list(a.retained_supports)+[contact_id]
    if a.finger!='pinky':
        plan.pop('pinky_support_geometry',None);plan['single_support_geometry']=geometry
        for stage in stages:stage['name']=stage['name'].replace('pinky','index')
    geometry['moving_finger']=a.finger;geometry['retained_supports']=a.retained_supports;geometry['ik_seed']=a.ik_seed;geometry['actual_slider_position_m']=slider
    plan['stages']+=stages
    path=a.output if valid else a.output.with_suffix('.rejected.json');path.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(dict(output=str(path),valid=valid,target=target.tolist(),point=actual_point.tolist(),min_knife_gap_m=min(v['knife_gap_m'] for v in sweep),min_self_gap_m=min(v['self_gap_m'] for v in sweep))))


if __name__=='__main__':main()
