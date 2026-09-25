"""One bounded 4DOF index RRT-Connect to an already screened free prepose."""
import argparse,json,os,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--proposal',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=2026092603);p.add_argument('--seconds',type=float,default=180.);p.add_argument('--iterations',type=int,default=800);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous path search')
    started=time.monotonic();plan=json.loads(a.proposal.read_text());m=plan['single_support_geometry'];d=json.loads(Path(m['source']).read_text());g=DigitGeometry(max_face_axes=32);full=DigitGeometry();q0=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife']);slider=m['actual_slider_position_m'];start=q0[:4].copy();goal=np.array(m['pre_q']);rng=np.random.default_rng(a.seed);checks=0
    def free(v,geometry=g):
        nonlocal checks
        checks+=1;q=q0.copy();q[:4]=v
        if geometry.minimum_gap(q,relative,slider,'index')<.0041:return False
        return all(s['gap_lower_bound_m']>=0 for s in geometry.self_gaps(q,'index'))
    def edge(x,y,geometry=g,resolution=.06):
        for u in np.linspace(0,1,max(2,int(np.ceil(np.max(abs(y-x))/resolution))+1)):
            if not free(x*(1-u)+y*u,geometry):return False
        return True
    if not free(start) or not free(goal):raise ValueError('RRT endpoints do not pass conservative clearance')
    trees=[dict(nodes=[start],parents=[-1]),dict(nodes=[goal],parents=[-1])];active=0;path=None;iterations=0
    def extend(tree,target):
        nodes=np.array(tree['nodes']);nearest=int(np.argmin(np.linalg.norm(nodes-target,axis=1)));x=nodes[nearest];delta=target-x;length=np.linalg.norm(delta);y=x+delta*min(1,.18/max(length,1e-10))
        if not edge(x,y):return None,False
        tree['nodes'].append(y);tree['parents'].append(nearest);return len(tree['nodes'])-1,length<=.18
    def chain(tree,j):
        values=[]
        while j>=0:values.append(tree['nodes'][j]);j=tree['parents'][j]
        return values[::-1]
    for iterations in range(a.iterations):
        if time.monotonic()-started>a.seconds or sum(len(t['nodes']) for t in trees)>=1600:break
        target=trees[1-active]['nodes'][0] if rng.random()<.15 else rng.uniform(g.w.lower[:4],g.w.upper[:4])
        j,_=extend(trees[active],target)
        if j is not None:
            target=trees[active]['nodes'][j]
            for _ in range(24):
                if time.monotonic()-started>a.seconds:break
                k,hit=extend(trees[1-active],target)
                if k is None:break
                if hit:
                    left=chain(trees[active],j);right=chain(trees[1-active],k)
                    path=(left+right[-2::-1]) if active==0 else (right+left[-2::-1]);break
        if path is not None:break
        active=1-active
    raw_path=None if path is None else [v.tolist() for v in path]
    if path is not None:
        # Bounded farthest-visible shortcutting; full dense validation follows.
        compact=[path[0]];i=0;shortcuts=0
        while i<len(path)-1:
            j=len(path)-1
            while j>i+1 and shortcuts<40:
                shortcuts+=1
                if edge(path[i],path[j]):break
                j-=1
            if shortcuts>=40:j=i+1
            compact.append(path[j]);i=j
        path=compact
    dense_valid=path is not None and all(edge(x,y,full,.025) for x,y in zip(path,path[1:]))
    report=dict(proposal=str(a.proposal),seed=a.seed,search_budget_seconds=a.seconds,search_iteration_limit=a.iterations,iterations=iterations+1,collision_checks=checks,
        elapsed_seconds=time.monotonic()-started,trees=[dict(nodes=[v.tolist() for v in t['nodes']],parents=t['parents']) for t in trees],raw_path=raw_path,
        path=None if path is None else [v.tolist() for v in path],full_geometry_sampled_pass=bool(dense_valid),
        scope='One bounded deterministic4DOF index RRT-Connect. Fixed actual wrist, knife, and other fingers for planning only. Whole index4.1mm clearance and finger-finger separation; search failure is not a global impossibility proof. No physical state reset.')
    if not dense_valid:
        out=a.output.with_suffix('.rejected.json');out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['trees','path','raw_path']}));return
    i=next(i for i,s in enumerate(plan['stages']) if s['name']=='index_under_clearance');stages=[];previous=np.array(d['close_q'])[:4]
    for j,v in enumerate(path[1:]):
        seconds=float(np.ceil(max(.5,1.875*np.max(abs(v-previous))/1.2)*30)/30)
        stages.append(dict(name='index_rrt_clearance_'+str(j+1),kind='move',moving_indices=list(range(4)),target=v.tolist(),seconds=seconds));previous=v
    plan['stages'][i:i+1]=stages;plan['rrt_clearance_geometry']=report;plan['composite_path_note']='Only the original rejected initial segment0 is replaced; original downstream prehold/touch/close/hold retained and screened. The failed direct sweep is retained as historical metadata.'
    a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),passed=True,waypoints=len(path),seconds=time.monotonic()-started,checks=checks)))


if __name__=='__main__':main()
