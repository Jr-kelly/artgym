"""Bounded constrained thumb escape; actual hand and wrist otherwise fixed."""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_wrist_plan import intersection_radius


def main():
    p=argparse.ArgumentParser()
    for name in ['source','prefix','rejected','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.with_suffix('.rejected.json').exists():raise ValueError('Preserve prior search')
    d=json.loads(a.source.read_text());g=DigitGeometry(max_face_axes=32);full=DigitGeometry();q0=np.array(d['touch_q']);cmd=np.array(d['close_q']);rel=np.array(d['wrist_in_knife']);slider=float(np.load(d['source_trace'])['slider'][d['source_step']])
    pairs=[('hand_r_thumb_'+x,'hand_r_base_link') for x in ['link3','link4','pad_link']]+[('hand_r_thumb_pad_link','hand_r_thumb_'+x) for x in ['link1','link2']]
    def pose(v):
        q=q0.copy();q[16:]=v;return q
    def own_gaps(q,geo):
        frames=geo.w.forward(q);out=[]
        for a,b in pairs:
            for va,na in geo.meshes[a]:
                fa=frames[a];va=va@fa[:3,:3].T+fa[:3,3];na=na@fa[:3,:3].T
                for vb,nb in geo.meshes[b]:
                    fb=frames[b];vb=vb@fb[:3,:3].T+fb[:3,3];nb=nb@fb[:3,:3].T;axes=np.r_[na,nb];pa=va@axes.T;pb=vb@axes.T
                    out.append(float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()))
        return out
    def constraints(v):
        q=pose(v)
        return np.r_[[s['gap_lower_bound_m']-.006 for s in g.gaps(q,rel,slider)],
            [s['gap_lower_bound_m']-.00015 for s in g.self_gaps(q,'thumb')],np.array(own_gaps(q,g))-.00005]
    old=json.loads(a.rejected.read_text());seed=np.array(old['stages'][-2]['target']);solutions=[]
    for label,initial in [('actual',q0[16:]),('rejected_exit',seed)]:
        result=minimize(lambda v:float(np.sum((v-q0[16:])**2)),initial,method='SLSQP',bounds=list(zip(g.w.lower[16:],g.w.upper[16:])),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=120,ftol=1e-10))
        v=result.x;q=pose(v);gap=full.minimum_gap(q,rel,slider);sg=min(s['gap_lower_bound_m'] for s in full.self_gaps(q,'thumb'));own=own_gaps(q,full)
        solutions.append(dict(seed=label,q=v.tolist(),solver_success=bool(result.success),message=str(result.message),knife_gap_m=gap,self_gap_m=sg,own_gaps_m=own,endpoint_pass=bool(gap>=.0041 and sg>=0 and min(own)>=0),objective=float(result.fun)))
    valid=[v for v in solutions if v['endpoint_pass']];report=dict(source=str(a.source),solutions=solutions,free_target_m=.006,retained_clearance_gate_m=.0041,
        scope='Two bounded constrained joint-space exits with fixed actual wrist, knife and non-thumb joints in planning. All physics still starts at table. Endpoint clearance plus full sampled path required, not just an anchor displacement.')
    if not valid:
        a.output.with_suffix('.rejected.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return
    selected=min(valid,key=lambda v:v['objective']);q1=pose(selected['q']);base=full.minimum_gap(q0,rel,slider);samples=[]
    for u in np.linspace(0,1,61):
        q=q0*(1-u)+q1*u;gap=full.minimum_gap(q,rel,slider);sg=min(s['gap_lower_bound_m'] for s in full.self_gaps(q,'thumb'));own=own_gaps(q,full)
        samples.append(dict(alpha=float(u),knife_gap_m=gap,self_gap_m=sg,own_gaps_m=own,passed=bool(gap>=min(base,0)-.0001 and sg>=0 and min(own)>=0)))
    report.update(selected_seed=selected['seed'],samples=samples,geometric_pass=all(s['passed'] for s in samples))
    if not report['geometric_pass']:
        a.output.with_suffix('.rejected.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='samples'}));return
    plan=json.loads(a.prefix.read_text());plan['thumb_escape_geometry']=report;plan['stages'] += [
        dict(name='thumb_escape_baseline_hold',kind='hold',seconds=1.,require_contacts=[0,1,2,3,4],required_initial_hand_command=cmd.tolist()),
        dict(name='thumb_escape_move',kind='move',seconds=max(1.,float(1.875*np.max(abs(q1-cmd)))),moving_indices=list(range(16,20)),target=selected['q']),
        dict(name='thumb_escape_hold',kind='hold',seconds=1.,require_contacts=[1,2,3,4],require_no_contact=0,require_thumb_gap_m=.0041)]
    a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(passed=True,output=str(a.output),solutions=solutions,minimum_gap_m=min(s['knife_gap_m'] for s in samples))))

if __name__=='__main__':main()
