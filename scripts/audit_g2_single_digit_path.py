"""Sample a single-digit suffix from an observed state; no physical state writes."""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_wrist_plan import intersection_radius


def main():
    p=argparse.ArgumentParser()
    for name in ['source','plan','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--start-stage',required=True);p.add_argument('--finger',default='thumb')
    p.add_argument('--final-gap',type=float,default=.0041);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous audit')
    d=json.loads(a.source.read_text());plan=json.loads(a.plan.read_text());g=DigitGeometry();w=g.w
    q0=np.array(d['touch_q']);q=q0.copy();command=np.array(d['close_q']);relative=np.array(d['wrist_in_knife'])
    trace=np.load(d['source_trace']);slider=float(trace['slider'][d['source_step']])
    ids=np.array([w.names.index('hand_r_'+a.finger+'_joint'+str(j)) for j in range(1,5)])
    others=np.array([j for j in range(20) if j not in ids]);base_gap=g.minimum_gap(q,relative,slider,a.finger)
    base={}
    for s in g.self_gaps(q,a.finger):
        if s['gap_lower_bound_m']<0:
            key=tuple(sorted([s['moving_link'],s['other_link']]))
            base[key]=intersection_radius(g,q,*key)
    if any(v is None for v in base.values()):raise ValueError('Unresolved initial self intersection')
    first=next(i for i,s in enumerate(plan['stages']) if s['name']==a.start_stage)
    rows=[];peak=0.;valid=True
    for s in plan['stages'][first:]:
        moving=s.get('moving_indices',[])
        if s['kind']!='move':continue
        if set(moving)!=set(ids) or 'arm_target' in s:raise ValueError('Suffix is not single-digit motor motion')
        goal=command.copy();goal[moving]=s['target']
        speed=float(1.875*np.abs(goal-command).max()/s['seconds']);peak=max(peak,speed)
        valid=valid and bool(np.all(goal>=w.lower) and np.all(goal<=w.upper) and speed<=2)
        q1=q.copy();q1[ids]=goal[ids]
        for alpha in np.linspace(0,1,41):
            v=q*(1-alpha)+q1*alpha;new=[]
            for pair in g.self_gaps(v,a.finger):
                if pair['gap_lower_bound_m']<0:
                    key=tuple(sorted([pair['moving_link'],pair['other_link']]))
                    radius=intersection_radius(g,v,*key)
                    if radius is None or radius>base.get(key,0)+1e-5:new.append(dict(pair=key,radius_m=radius))
            rows.append(dict(stage=s['name'],alpha=float(alpha),whole_digit_gap_m=g.minimum_gap(v,relative,slider,a.finger),new_or_increased_intersections=new))
        q=q1;command=goal
    if not rows:raise ValueError('No new movement to audit')
    valid=valid and bool(min(v['whole_digit_gap_m'] for v in rows)>=min(base_gap,0)-.0001 and rows[-1]['whole_digit_gap_m']>=a.final_gap and not any(v['new_or_increased_intersections'] for v in rows))
    out=dict(source=str(a.source),plan=str(a.plan),start_stage=a.start_stage,geometric_pass=valid,
        initial_gap_m=base_gap,final_gap_m=rows[-1]['whole_digit_gap_m'],minimum_gap_m=min(v['whole_digit_gap_m'] for v in rows),
        peak_command_rad_s=peak,support_nominal_displacement_rad=float(np.abs(q[others]-q0[others]).max()),samples=rows,
        limitation='Observed start q to unloaded motor endpoint with fixed measured wrist/knife. Contact compliance and dynamic tracking are not certified. Initial motor offset retained for speed check; no sensor force estimate or state reset.')
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='samples'}))


if __name__=='__main__':main()
