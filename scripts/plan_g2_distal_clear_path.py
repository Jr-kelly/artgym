"""Bounded2D joint-space search for an unloaded index finger around the knife.

Only index distal joints move. The root joints and all three actual supporting
digits remain fixed. Grid/interpolation checks are geometry, not physical proof.
"""
import argparse,json,heapq,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--contact-corridor',action='store_true',help='Explicit index surface-migration alternative: allow physical index contact while geometric surfaces remain separated0.2mm; does not relax thumb clearance or object stability.')
    a=p.parse_args();corridor=.0002 if a.contact_corridor else .0041
    if a.output.exists():raise ValueError('Preserve prior search')
    d=json.loads(a.source.read_text());proposal=json.loads(a.proposal.read_text());g=DigitGeometry(max_face_axes=32);full=DigitGeometry();w=g.w;q=np.array(d['touch_q']);R=np.array(d['wrist_in_knife']);goal=np.array(proposal['new_distal_geometry']['distal_q']);start=q[2:4].copy()
    initial_self={(v['moving_link'],v['other_link']):min(v['gap_lower_bound_m'],0) for v in g.self_gaps(q,'index')}
    def check(v):
        qs=q.copy();qs[2:4]=v;gap=g.minimum_gap(qs,R,-.032674588,'index')
        good=all(s['gap_lower_bound_m']>=initial_self[(s['moving_link'],s['other_link'])]-1e-5 for s in g.self_gaps(qs,'index'))
        return gap,good
    def segment(x,y,threshold,n=11):
        rows=[check(x*(1-u)+y*u) for u in np.linspace(0,1,n)]
        return min(z[0] for z in rows)>=threshold and all(z[1] for z in rows)
    axis0=np.linspace(max(w.lower[2],.10),min(w.upper[2],1.25),47);axis1=np.linspace(max(w.lower[3],.50),w.upper[3],44)
    positions=np.array(np.meshgrid(axis0,axis1,indexing='ij')).transpose(1,2,0);free=np.zeros(positions.shape[:2],bool);gaps=np.zeros(free.shape)
    for i in range(len(axis0)):
        for j in range(len(axis1)):
            gap,good=check(positions[i,j]);gaps[i,j]=gap;free[i,j]=good and gap>=corridor
    np.savez_compressed(a.output.with_suffix('.grid.npz'),positions=positions,free=free,gaps_m=gaps)
    free_ids=[tuple(v) for v in np.argwhere(free)];start_gap=check(start)[0];end_gap=check(goal)[0]
    starts=[v for v in sorted(free_ids,key=lambda i:np.linalg.norm(positions[i]-start))[:60] if segment(start,positions[v],min(start_gap,0)-1e-5)]
    ends=[v for v in sorted(free_ids,key=lambda i:np.linalg.norm(positions[i]-goal))[:60] if segment(positions[v],goal,min(end_gap,0)-1e-4)]
    result=dict(source=str(a.source),proposal=str(a.proposal),grid_shape=list(free.shape),free_nodes=len(free_ids),start_connections=len(starts),end_connections=len(ends),start_gap_m=start_gap,close_command_gap_m=end_gap,
        corridor_gap_m=corridor,contact_migration=a.contact_corridor,
        scope='Only2index distal motors. Explicit contact corridor allows contact-offset forces and surface migration; it is not unloaded motion. Standard free corridor is4.1mm. Initial escape preserves geometry; final finite-drive contact approach no deeper overlap than goal+0.1mm. Thumb clearance and fixed-world criteria unchanged. Geometry only.')
    path=None
    if starts and ends:
        targets=set(ends);cost={v:float(np.linalg.norm(positions[v]-start)) for v in starts};prev={v:None for v in starts};queue=[(val,v) for v,val in cost.items()];heapq.heapify(queue)
        while queue:
            value,node=heapq.heappop(queue)
            if value>cost[node]+1e-10:continue
            if node in targets:
                path=[];cur=node
                while cur is not None:path.append(positions[cur]);cur=prev[cur]
                path=path[::-1];break
            for di,dj in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                nxt=(node[0]+di,node[1]+dj)
                if not(0<=nxt[0]<free.shape[0] and 0<=nxt[1]<free.shape[1] and free[nxt]):continue
                cand=value+float(np.linalg.norm(positions[nxt]-positions[node]))
                if cand<cost.get(nxt,float('inf')) and segment(positions[node],positions[nxt],corridor,3):cost[nxt]=cand;prev[nxt]=node;heapq.heappush(queue,(cand,nxt))
    if path is None:
        result['geometric_pass']=False;a.output.with_suffix('.rejected.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return
    simplified=[path[0]];i=0
    while i<len(path)-1:
        nxt=next(j for j in range(len(path)-1,i,-1) if segment(path[i],path[j],corridor,31));simplified.append(path[nxt]);i=nxt
    nodes=[start]+simplified+[goal];audit=[]
    for j,(x,y) in enumerate(zip(nodes[:-1],nodes[1:])):
        for u in np.linspace(0,1,31):
            qs=q.copy();qs[2:4]=x*(1-u)+y*u;audit.append(dict(segment=j,alpha=float(u),whole_index_gap_m=full.minimum_gap(qs,R,-.032674588,'index')))
    result.update(geometric_pass=True,distal_waypoints=[v.tolist() for v in nodes],full_geometry_sweep=audit)
    plan=json.loads(a.prefix.read_text());stages=[]
    for j,y in enumerate(nodes[1:]):
        seconds=max(1.5 if j==0 else (2. if j==len(nodes)-2 else .5),1.875*np.max(abs(y-nodes[j]))/.5)
        stages.append(dict(name='pinky_supported_index_path_'+str(j),kind='move',moving_indices=[2,3],target=y.tolist(),seconds=seconds,require_thumb_gap_m=.0041))
        if j==0:stages.append(dict(name='pinky_supported_index_corridor_hold' if a.contact_corridor else 'pinky_supported_index_free_hold',kind='hold',seconds=1.,require_contacts=[2,3,4],require_no_contact=0 if a.contact_corridor else 1,require_thumb_gap_m=.0041))
    stages.append(dict(name='pinky_index_four_support_hold',kind='hold',seconds=1.,require_contacts=[1,2,3,4],require_no_contact=0,require_thumb_gap_m=.0041))
    plan['stages']+=stages;plan['distal_clear_path']=result;a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='full_geometry_sweep'}))


if __name__=='__main__':main()
