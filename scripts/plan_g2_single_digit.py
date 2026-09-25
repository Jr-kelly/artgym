"""One-digit contact migration from a measured freely executed flip endpoint."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_seating_feedback import ContactCorrection
from scripts.wuji_kinematics import FINGERS


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--finger',choices=FINGERS,default='middle');p.add_argument('--mode',choices=['unload','reseat'],default='unload')
    p.add_argument('--prefix-plan',type=Path,help='Reuse an already physically verified sequence before the new single-digit stages.')
    p.add_argument('--multi-seed',action='store_true',help='Bounded three extra joint-space IK seeds, only for a rejected geometric contact.')
    p.add_argument('--contact-z',type=float,help='Explicit longitudinal bottom-contact location in knife coordinates; preserves the outside-corner clearance path.')
    p.add_argument('--contact-x',type=float,default=.009,help='Bottom support x coordinate; interior supports must be verified by actual contact normal.')
    p.add_argument('--unload-gap',type=float,default=.004,help='Geometric displacement in m, not measured force; default original 4mm.')
    p.add_argument('--actual-contact-anchor',action='store_true',help='Unload using the material point recorded at the actual contacting link, rather than a mesh extreme.')
    a=p.parse_args();data=json.loads(a.source.read_text());c=ContactCorrection();w=c.w
    q=np.asarray(data['touch_q'],dtype=float);cmd=np.asarray(data['close_q'],dtype=float);relative=np.asarray(data['wrist_in_knife'])
    normals=np.asarray(data['contact_normals']);idx=FINGERS.index(a.finger)
    inds=[w.names.index('hand_r_'+a.finger+'_joint'+str(i)) for i in range(1,5)]
    point=c.contacts(q,relative,normals)[0][idx]
    anchor=None
    if a.actual_contact_anchor:
        if a.mode!='unload':raise ValueError('Actual material anchor currently supports unload only')
        rows=[json.loads(line) for line in (Path(data['source_trial'])/'knife-contact-pairs.jsonl').read_text().splitlines()]
        samples=[]
        for row in rows:
            if not data['source_step']-4<=row['step']<=data['source_step']:continue
            for side in [0,1]:
                if '_'+a.finger+'_' in row['body'+str(side)] and 'localPos'+str(side) in row:
                    samples.append((row['body'+str(side)],row['localPos'+str(side)]))
        if not samples:raise ValueError('No actual material contact anchor for '+a.finger)
        link=max({s[0] for s in samples},key=lambda n:sum(s[0]==n for s in samples))
        local=np.mean([s[1] for s in samples if s[0]==link],axis=0)
        anchor=dict(link=link,local_point=local.tolist(),source_step=data['source_step'])
        def material_point(values):
            frame=relative@w.forward(values)[link]
            return frame[:3,:3]@local+frame[:3,3]
        point=material_point(q)
    stages=[dict(name='baseline_hold',kind='hold',seconds=1.)];geometry=[]
    def solve(name,target,normal,seconds=1.):
        nonlocal q
        ns=normals.copy();ns[idx]=normal
        def residual(values):
            proposed=q.copy();proposed[inds]=values
            pos=material_point(proposed) if anchor is not None else c.contacts(proposed,relative,ns)[0][idx]
            return np.r_[(pos-target)*200,(values-q[inds])*.015]
        result=least_squares(residual,np.clip(q[inds],w.lower[inds]+1e-6,w.upper[inds]-1e-6),bounds=(w.lower[inds],w.upper[inds]),max_nfev=160,diff_step=1e-5)
        if a.multi_seed and np.linalg.norm(residual(result.x)[:3]/200)>.001:
            for seed in [[0,0,1.5,.5],[.7,0,1.3,.5],[.3,.1,1.5,.8]]:
                retry=least_squares(residual,np.clip(seed,w.lower[inds]+1e-6,w.upper[inds]-1e-6),bounds=(w.lower[inds],w.upper[inds]),max_nfev=160,diff_step=1e-5)
                if retry.cost<result.cost:result=retry
        error=float(np.linalg.norm(residual(result.x)[:3]/200));q[inds]=result.x
        geometry.append(dict(name=name,point=target.tolist(),normal=normal.tolist(),error_m=error))
        if error>.001:
            a.output.with_suffix('.rejected.json').write_text(json.dumps(dict(status='geometry_rejected',source=str(a.source),geometry=geometry),indent=2)+'\n')
            raise ValueError('Digit IK exceeds 1mm: '+str(geometry[-1]))
        stages.append(dict(name=name,kind='move',moving_indices=inds,target=result.x.tolist(),seconds=seconds))
    solve('unload_'+a.finger,point+normals[idx]*a.unload_gap,normals[idx])
    stages.append(dict(name='unloaded_hold',kind='hold',seconds=1.,require_no_contact=idx))
    if a.mode=='reseat':
        target=point.copy();target[0]=.0135;target[1]=-.005
        if a.contact_z is not None:target[2]=a.contact_z
        solve('corner_clearance',target,np.array([1.,0.,0.]),2.)
        target[0]=a.contact_x
        solve('under_body',target,np.array([0.,-1.,0.]),2.)
        target[1]=-.003
        solve('establish_bottom',target,np.array([0.,-1.,0.]),2.)
        stages.append(dict(name='new_support_hold',kind='hold',seconds=1.,require_contact=idx))
    plan=dict(object_reference='fixed_world_at_gait_start',initial_command=cmd.tolist(),stages=stages,
        source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),finger=a.finger,
        support_fingers=[f for f in FINGERS if f!=a.finger],geometry=geometry,contact_z=a.contact_z,actual_contact_anchor=anchor,
        method='Move one digit only. Other motor targets and the wrist remain fixed. Geometry uses the actual_contact_anchor if supplied, otherwise a collision mesh support estimate. No measured force inference.')
    if a.prefix_plan:
        prefix=json.loads(a.prefix_plan.read_text())
        for stage in stages:stage['name']=a.finger+'_'+stage['name']
        stages[0]['required_initial_hand_command']=cmd.tolist()
        # Preserve the controllers that generated the physical prefix. Stop
        # their residual updates at its boundary, retaining the actual target.
        configs=prefix.get('normal_feedback_segments',([prefix['normal_feedback']] if 'normal_feedback' in prefix else []))
        for config in configs:config.setdefault('stop_after_stage',prefix['stages'][-1]['name'])
        plan={**prefix,**plan,'initial_command':prefix['initial_command'],
            'object_reference':prefix['object_reference'],'stages':prefix['stages']+stages,'prefix':str(a.prefix_plan)}
    a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),geometry=geometry)))


if __name__=='__main__':main()
