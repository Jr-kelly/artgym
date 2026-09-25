"""Bounded ordered-joint approach to a collision-free index pre-contact pose.

Only index motors change. Retains the measured continuous prefix and the
previously screened final approach/close; no state reset or contact assumption.
"""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--proposal',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--abduct-first',action='store_true',help='Two explicit joint2 clearance detours, after the direct joint-order comparisons failed.');a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous proposal')
    plan=json.loads(a.proposal.read_text());m=plan['single_support_geometry'];d=json.loads(Path(m['source']).read_text());g=DigitGeometry();q0=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife']);end=np.array(m['pre_q']);slider=m['actual_slider_position_m']
    # Two physically meaningful group orders, then two flexion orders if needed.
    orders=[[[2,3],[0,1]],[[0,1],[2,3]],[[3],[2],[0,1]],[[2],[3],[0,1]]]
    candidates=[]
    if a.abduct_first:
        for label,value in [('joint2_lower',g.w.lower[1]+.02),('joint2_upper',g.w.upper[1]-.02)]:
            first=q0[:4].copy();first[1]=value;second=first.copy();second[2:4]=end[2:4]
            candidates.append((label,[first,second,end]))
    else:
        for order in orders:
            previous=q0[:4].copy();goals=[]
            for group in order:
                previous=previous.copy();previous[group]=end[group];goals.append(previous)
            candidates.append((order,goals))
    attempts=[];chosen=None
    for order,goals in candidates:
        q=q0.copy();rows=[];waypoints=[];valid=True
        for target in goals:
            goal=q.copy();goal[:4]=target
            for u in np.linspace(0,1,31):
                v=q*(1-u)+goal*u;gap=g.minimum_gap(v,relative,slider,'index');sg=min(s['gap_lower_bound_m'] for s in g.self_gaps(v,'index'))
                rows.append(dict(segment=len(waypoints),alpha=float(u),knife_gap_m=gap,self_gap_m=sg))
                if gap<.0041 or sg<0:valid=False;break
            waypoints.append(goal[:4].tolist());q=goal
            if not valid:break
        attempts.append(dict(order=order,valid=valid,waypoints=waypoints,samples=rows))
        if valid:chosen=attempts[-1];break
    result=dict(proposal=str(a.proposal),attempts=attempts,selected=None if chosen is None else chosen['order'],abduct_first=a.abduct_first,scope='At most four ordered joint paths or two declared joint2 detours. All other measured joints fixed. Whole-finger4.1mm free clearance until prepose, positive finger-finger separation; physical support still to be tested.')
    if chosen is None:
        out=a.output.with_suffix('.rejected.json');out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(output=str(out),valid=False)));return
    i=next(i for i,s in enumerate(plan['stages']) if s['name']=='index_under_clearance');old=plan['stages'][i];stages=[];previous=np.array(d['close_q'])[:4]
    for j,goal in enumerate(chosen['waypoints']):
        stages.append(dict(name='index_ordered_clearance_'+str(j+1),kind='move',moving_indices=list(range(4)),target=goal,seconds=max(1.,1.875*float(np.max(abs(np.array(goal)-previous)))/1.2)))
        previous=np.array(goal)
    plan['stages'][i:i+1]=stages;plan['ordered_index_geometry']=result
    a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),valid=True,order=chosen['order'],min_knife_gap_m=min(s['knife_gap_m'] for s in chosen['samples']),min_self_gap_m=min(s['self_gap_m'] for s in chosen['samples']))))


if __name__=='__main__':main()
