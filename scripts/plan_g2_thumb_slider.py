"""Bounded thumb-only free-space routing followed by contact with the actual slider.

A screened surface solution is only an IK seed. All geometry is recomputed from
one measured frame, and the full continuous table prefix remains in the plan.
"""
import argparse,json,os,time,itertools
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares, minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_wrist_plan import intersection_radius


def main():
    p=argparse.ArgumentParser()
    for name in ['source','prefix','screen','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--retained-supports',type=int,nargs='+',default=[1,2,3,4],help='Previously evidenced non-thumb contact indices retained at all new holds.')
    p.add_argument('--branch',default='bounded_1');p.add_argument('--seed',type=int,default=2026092605)
    p.add_argument('--seconds',type=float,default=180.);p.add_argument('--iterations',type=int,default=800)
    p.add_argument('--normal-close',type=float,default=.0008)
    p.add_argument('--contact-corridor',action='store_true',help='Distinct migration mode: positive0.2mm geometry clearance allows PhysX proximity contact during transit. G1 and prepose release holds remain4.1mm/no-contact; no dynamics success inferred.')
    p.add_argument('--fold-fourth-q',type=float,help='Explicit deeper transient fourth-joint fold, within original limit; unroll to contact prepose afterwards.')
    p.add_argument('--fold-first',action='store_true',help='One explicit fourth-joint folding waypoint; screen six orders of the remaining three joints before bounded RRT.')
    p.add_argument('--free-prepose',action='store_true',help='Find nearest collision-free joint prepose instead of imposing an unreachable straight12mm material-point offset.')
    a=p.parse_args()
    if a.output.exists() or a.output.with_suffix('.rejected.json').exists():raise ValueError('Preserve previous search')
    if not a.retained_supports or any(i not in [1,2,3,4] for i in a.retained_supports):raise ValueError('Need declared non-thumb supports')
    if not 0<=a.normal_close<=.001:raise ValueError('Bounded motor closing offset only')
    data=json.loads(a.source.read_text());screen=json.loads(a.screen.read_text());branch=next(v for v in screen['rows'] if v['seed']==a.branch)
    if not branch['geometric_candidate']:raise ValueError('Require a positive screened branch')
    g=DigitGeometry(max_face_axes=32);full=DigitGeometry();w=g.w
    q0=np.array(data['touch_q']);cmd=np.array(data['close_q']);relative=np.array(data['wrist_in_knife']);slider=float(np.load(data['source_trace'])['slider'][data['source_step']])
    anchor=np.array(branch['anchor_local']);link=screen['contact_link'];target=np.array(branch['target']);target[2]+=slider-screen['slider_position_m']
    own_pairs=[('hand_r_thumb_'+suffix,'hand_r_base_link') for suffix in ['link3','link4','pad_link']]+[('hand_r_thumb_pad_link','hand_r_thumb_'+suffix) for suffix in ['link1','link2']]
    base_own={pair:intersection_radius(full,q0,*pair) for pair in own_pairs}
    if any(v is None for v in base_own.values()):raise ValueError('Unresolved initial own-link geometry')
    def proposed(v):
        q=q0.copy();q[16:]=v;return q
    def point(v):
        f=relative@w.forward(proposed(v))[link];return f[:3,:3]@anchor+f[:3,3]
    def solve(pt,seed,gap):
        def residual(v):
            q=proposed(v)
            return np.r_[(point(v)-pt)*300,[min(s['gap_lower_bound_m']-gap,0)*600 for s in g.gaps(q,relative,slider)],
                [min(s['gap_lower_bound_m']-.00015,0)*400 for s in g.self_gaps(q,'thumb')],(v-seed)*.005]
        return least_squares(residual,np.clip(seed,w.lower[16:]+1e-7,w.upper[16:]-1e-7),bounds=(w.lower[16:],w.upper[16:]),max_nfev=180,diff_step=1e-5)
    touch=solve(target,np.array(branch['q']),-.0003)
    prepoint=target+np.array([0,.012,0]);pre=solve(prepoint,touch.x,.0048)
    prepose_method='straight12mm material-point offset'
    if a.free_prepose:
        def constraints(v):
            q=proposed(v)
            return np.r_[[s['gap_lower_bound_m']-.0048 for s in g.gaps(q,relative,slider)],
                [s['gap_lower_bound_m']-.00015 for s in g.self_gaps(q,'thumb')],
                [s['gap_lower_bound_m']-.00005 for s in g.pair_gaps(q,own_pairs)]]
        pre=minimize(lambda v:float(np.sum((v-touch.x)**2)),pre.x,method='SLSQP',bounds=list(zip(w.lower[16:],w.upper[16:])),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=120,ftol=1e-10))
        prepoint=point(pre.x);prepose_method='nearest joint-space prepose constrained to4.8mm clearance; no fixed material-point translation demand'
    closepoint=target-np.array([0,a.normal_close,0]);close=solve(closepoint,touch.x,-.0011)
    endpoints=[]
    for name,result,pt,bound in [('pre',pre,prepoint,.0041),('touch',touch,target,-.0005),('close',close,closepoint,-.0012)]:
        q=proposed(result.x);gap=full.minimum_gap(q,relative,slider);sg=min(s['gap_lower_bound_m'] for s in full.self_gaps(q,'thumb'))
        endpoints.append(dict(name=name,q=result.x.tolist(),target=pt.tolist(),point=point(result.x).tolist(),error_m=float(np.linalg.norm(point(result.x)-pt)),whole_thumb_gap_m=gap,self_gap_m=sg,passed=bool(np.linalg.norm(point(result.x)-pt)<.001 and gap>=bound and sg>=0)))
    report=dict(source=str(a.source),screen=str(a.screen),branch=a.branch,actual_slider_position_m=slider,anchor_local=anchor.tolist(),contact_link=link,endpoints=endpoints,
        prepose_method=prepose_method,prepose_solver_success=bool(pre.success),seed=a.seed,seconds_budget=a.seconds,iteration_budget=a.iterations,normal_motor_close_m=a.normal_close,
        scope='Only thumb motors move after complete actual table prefix. IK material point on screened pad; free path requires full-thumb4.1mm clearance. Contact commands are finite drive, not measured force or physical penetration. No object state writes.')
    def save_reject(reason):
        report.update(geometric_pass=False,rejection=reason);a.output.with_suffix('.rejected.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=False,reason=reason,endpoints=endpoints)))
    if not all(v['passed'] for v in endpoints):save_reject('endpoint geometry');return
    path_gap=.0002 if a.contact_corridor else .0041
    report['path_clearance_m']=path_gap
    report['transit_contact_mode']='PhysX proximity contacts explicitly allowed during migration; not a free-space motion' if a.contact_corridor else 'full4.1mm free space'
    report['scope']='Only thumb motors move after actual table prefix. '+report['transit_contact_mode']+'. G1 and final prepose still require4.1mm/no-contact hold. Finite drive contact commands are not measured force or physical penetration; no object state writes.'
    checks=0;started=time.monotonic();rng=np.random.default_rng(a.seed)
    def free(v,geometry=g):
        nonlocal checks
        checks+=1;q=proposed(v)
        return (geometry.minimum_gap(q,relative,slider)>=path_gap
            and all(s['gap_lower_bound_m']>=0 for s in geometry.self_gaps(q,'thumb'))
            and all(s['gap_lower_bound_m']>=0 for s in geometry.pair_gaps(q,own_pairs)))
    def edge(x,y,geometry=g,resolution=.06):
        return all(free(x*(1-u)+y*u,geometry) for u in np.linspace(0,1,max(2,int(np.ceil(np.max(abs(y-x))/resolution))+1)))
    start=q0[16:];goal=pre.x
    if not free(start) or not free(goal):save_reject('free-path endpoint');return
    path=[start,goal] if edge(start,goal) else None
    fold=None;ordered=[]
    if path is None and a.fold_first:
        candidate=start.copy();candidate[3]=goal[3] if a.fold_fourth_q is None else a.fold_fourth_q
        if not w.lower[19]<=candidate[3]<=w.upper[19]:raise ValueError('Transient fold exceeds original joint limit')
        if edge(start,candidate):
            fold=candidate
            for order in itertools.permutations([0,1,2]):
                proposed_path=[start.copy(),fold.copy()];previous=fold.copy();passed=True
                for j in order:
                    target=previous.copy();target[j]=goal[j]
                    if not edge(previous,target):passed=False;break
                    proposed_path.append(target);previous=target
                if passed and not np.array_equal(previous,goal):
                    passed=edge(previous,goal)
                    if passed:proposed_path.append(goal.copy())
                ordered.append(dict(order=[j+1 for j in order],passed=passed))
                if passed:path=proposed_path;break
    report['fold_first_screen']=dict(requested=a.fold_first,fold_waypoint=None if fold is None else fold.tolist(),ordered_checks=ordered)
    search_start=start if fold is None else fold
    trees=[dict(nodes=[search_start],parents=[-1]),dict(nodes=[goal],parents=[-1])];active=0;iterations=0
    def extend(tree,target):
        j=int(np.argmin(np.linalg.norm(np.array(tree['nodes'])-target,axis=1)));x=tree['nodes'][j];delta=target-x;length=np.linalg.norm(delta);y=x+delta*min(1,.18/max(length,1e-10))
        if not edge(x,y):return None,False
        tree['nodes'].append(y);tree['parents'].append(j);return len(tree['nodes'])-1,length<=.18
    def chain(tree,j):
        rows=[]
        while j>=0:rows.append(tree['nodes'][j]);j=tree['parents'][j]
        return rows[::-1]
    while path is None and iterations<a.iterations and time.monotonic()-started<a.seconds and sum(len(t['nodes']) for t in trees)<1600:
        iterations+=1;sample=trees[1-active]['nodes'][0] if rng.random()<.15 else rng.uniform(w.lower[16:],w.upper[16:]);j,_=extend(trees[active],sample)
        if j is not None:
            for _ in range(24):
                if time.monotonic()-started>a.seconds:break
                k,hit=extend(trees[1-active],trees[active]['nodes'][j])
                if k is None:break
                if hit:
                    left=chain(trees[active],j);right=chain(trees[1-active],k);path=left+right[-2::-1] if active==0 else right+left[-2::-1]
                    if fold is not None:path=[start]+path
                    break
        active=1-active
    report.update(tree_nodes=[len(t['nodes']) for t in trees],trees=[dict(nodes=[v.tolist() for v in t['nodes']],parents=t['parents']) for t in trees],iterations=iterations,collision_checks=checks,search_seconds=time.monotonic()-started,raw_path=None if path is None else [v.tolist() for v in path])
    if path is None:save_reject('bounded free-space search exhausted');return
    compact=[path[0]];i=0;shortcuts=0
    while i<len(path)-1:
        j=len(path)-1
        while j>i+1 and shortcuts<40:
            shortcuts+=1
            if edge(path[i],path[j]):break
            j-=1
        if shortcuts>=40:j=i+1
        compact.append(path[j]);i=j
    path=compact;report['path']=[v.tolist() for v in path]
    if not all(edge(x,y,full,.025) for x,y in zip(path,path[1:])):save_reject('dense full-geometry free path');return
    samples=[]
    for name,x,y,bound in [('approach',pre.x,touch.x,-.0005),('close',touch.x,close.x,-.0012)]:
        for u in np.linspace(0,1,41):
            q=proposed(x*(1-u)+y*u);gap=full.minimum_gap(q,relative,slider);sg=min(s['gap_lower_bound_m'] for s in full.self_gaps(q,'thumb'))
            samples.append(dict(segment=name,alpha=float(u),knife_gap_m=gap,self_gap_m=sg,passed=bool(gap>=bound and sg>=0)))
    report['contact_path_samples']=samples
    if not all(v['passed'] for v in samples):save_reject('contact approach or finite-drive closing sweep');return
    own_bad=[]
    for j,(x,y) in enumerate(zip(path+[touch.x],path[1:]+[touch.x,close.x])):
        for u in np.linspace(0,1,21):
            q=proposed(x*(1-u)+y*u)
            for pair in own_pairs:
                radius=intersection_radius(full,q,*pair)
                if radius is None or radius>base_own[pair]+1e-5:own_bad.append(dict(segment=j,alpha=float(u),pair=pair,radius=radius))
    report['own_link_palm_new_intersections']=own_bad
    if own_bad:save_reject('own-link or palm');return
    plan=json.loads(a.prefix.read_text())
    configs=plan.get('normal_feedback_segments',([plan['normal_feedback']] if 'normal_feedback' in plan else []))
    for config in configs:config.setdefault('stop_after_stage',plan['stages'][-1]['name'])
    report['retained_contact_indices']=a.retained_supports
    stages=[dict(name='thumb_slider_start_hold',kind='hold',seconds=1.,required_initial_hand_command=cmd.tolist(),require_contacts=a.retained_supports,require_no_contact=0,require_thumb_gap_m=.0041)];previous=cmd[16:]
    for j,v in enumerate(path[1:]):
        seconds=float(np.ceil(max(1.,1.875*np.max(abs(v-previous))/1.2)*30)/30)
        stage=dict(name=('thumb_slider_contact_corridor_' if a.contact_corridor else 'thumb_slider_free_')+str(j+1),kind='move',moving_indices=list(range(16,20)),target=v.tolist(),seconds=seconds)
        if not a.contact_corridor:stage['require_thumb_gap_m']=.0041
        stages.append(stage);previous=v
    stages += [dict(name='thumb_slider_pre_hold',kind='hold',seconds=1.,require_contacts=a.retained_supports,require_no_contact=0,require_thumb_gap_m=.0041),
        dict(name='thumb_slider_touch',kind='move',moving_indices=list(range(16,20)),target=touch.x.tolist(),seconds=2.),
        dict(name='thumb_slider_close',kind='move',moving_indices=list(range(16,20)),target=close.x.tolist(),seconds=1.),
        dict(name='thumb_slider_contact_hold',kind='hold',seconds=1.,require_contacts=[0]+a.retained_supports,require_slider_contact=0)]
    report['geometric_pass']=True;plan['thumb_slider_geometry']=report;plan['stages']+=stages
    a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(passed=True,output=str(a.output),waypoints=len(path),endpoints=endpoints)))

if __name__=='__main__':main()
