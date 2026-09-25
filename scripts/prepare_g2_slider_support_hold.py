"""Prepare one middle-finger feedback control from the failed static hold.

No physics or state reset. The static trace is used only to choose and audit a
robot controller. Geometry samples and shadow residuals are not a success test.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform
from scripts.g2_normal_feedback import NormalFeedback
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_wrist_plan import intersection_radius


def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True)
    p.add_argument('--base-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--error-components',choices=['normal','position'],default='normal')
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    t=np.load(a.trial/'trace.npz');i=int(np.flatnonzero(t['phase']=='settle_history')[0]-1)
    physics=json.loads((a.trial/'physics.json').read_text());ids=physics['hand_indices'];g=DigitGeometry()
    obj=transform(t['object'][i,:3],t['object'][i,3:]);wrist=transform(t['wrist'][i,:3],t['wrist'][i,3:])
    contacts=[]
    for line in (a.trial/'knife-contact-pairs.jsonl').open():
        row=json.loads(line)
        if row['step']==i and row['body0']=='link_0' and row['body1']=='hand_r_middle_pad_link' and row['lambda_value']>1e-6:contacts.append(row)
    if not contacts:raise ValueError('No effective actual middle-pad contact at controller initialization')
    normal=obj[:3,:3].T@np.mean([v['normal'] for v in contacts],axis=0);normal/=np.linalg.norm(normal)
    config=dict(start_stage='slider_support_feedback_hold22',stop_after_stage='slider_support_feedback_hold22',
        indices=[6,7],link='hand_r_middle_pad_link',anchor_local=np.mean([v['localPos1'] for v in contacts],axis=0).tolist(),
        normal_in_knife=normal.tolist(),integral_gain_per_s=3.,max_correction_rad=.08,
        max_correction_rate_rad_s=.2,jacobian_damping_m2=1e-6,reference_frame='knife',error_components=a.error_components)
    q=t['q'][i];nominal=t['reference_targets'][i,ids]
    controller=NormalFeedback(g.w,config,q,wrist,obj,1/30)
    first,first_diagnostic=controller.step(nominal,q,wrist,obj)
    assert np.max(np.abs(first-nominal))<1e-7
    shadow=[]
    for j in range(i+1,len(t['time'])):
        w=transform(t['wrist'][j,:3],t['wrist'][j,3:]);o=transform(t['object'][j,:3],t['object'][j,3:])
        _,d=controller.step(nominal,t['q'][j],w,o)
        shadow.append(dict(time_s=float(t['time'][j]),**d))
    # Actual and motor-reference envelopes are separate; neither is a force.
    checked=[];rejected=[]
    own_pairs=[('hand_r_middle_'+suffix,'hand_r_base_link') for suffix in ['link3','link4','pad_link']]+[('hand_r_middle_pad_link','hand_r_middle_'+suffix) for suffix in ['link1','link2']]
    for origin_name,origin in [('actual',q),('motor_reference',nominal)]:
        base={(r['moving_link'],r['other_link']):r for r in g.self_gaps(origin,'middle')}
        radii={pair:intersection_radius(g,origin,*pair) for pair,r in base.items() if r['gap_lower_bound_m']<0}
        own_base={pair:intersection_radius(g,origin,*pair) for pair in own_pairs}
        for d0 in [-.08,0,.08]:
            for d1 in [-.08,0,.08]:
                value=origin.copy();value[[6,7]]+=np.array([d0,d1]);value=np.clip(value,g.w.lower,g.w.upper)
                for r in g.self_gaps(value,'middle'):
                    if r['gap_lower_bound_m']>=0:continue
                    pair=(r['moving_link'],r['other_link']);radius=intersection_radius(g,value,*pair)
                    old=radii.get(pair,0.)
                    if radius is None or old is None or radius>old+1e-6:rejected.append(dict(origin=origin_name,delta=[d0,d1],pair=pair,initial_radius_m=old,new_radius_m=radius))
                for pair in own_pairs:
                    radius=intersection_radius(g,value,*pair);old=own_base[pair]
                    if radius is None or old is None or radius>old+1e-6:rejected.append(dict(origin=origin_name,delta=[d0,d1],pair=pair,initial_radius_m=old,new_radius_m=radius))
                checked.append(dict(origin=origin_name,delta=[d0,d1]))
    result=dict(source_trial=str(a.trial),source_frame=i,source_time_s=float(t['time'][i]),
        trace_sha256=hashlib.sha256((a.trial/'trace.npz').read_bytes()).hexdigest(),
        first_command_change_rad=float(np.max(np.abs(first-nominal))),first_feedback=first_diagnostic,
        feedback=config,geometry_samples=checked,rejected=rejected,shadow=shadow,
        passed=not rejected,scope='Shadow feedback uses unchanged baseline states and is not a closed-loop simulation. Convex samples check new inter-finger intersections, not continuous collision certification.')
    a.output.with_suffix('.preflight.json').write_text(json.dumps(result,indent=2)+'\n')
    if rejected:raise ValueError('Feedback envelope has new/increased intersections')
    plan=json.loads(a.base_plan.read_text());plan.setdefault('normal_feedback_segments',[]).append(config)
    plan['stages'].append(dict(name=config['start_stage'],kind='hold',seconds=22.,require_contacts=[0,1,2,4],require_slider_contact=0))
    plan['support_hold_control']=dict(source_trial=str(a.trial),source_frame=i,
        planned_change='Only middle distal '+a.error_components+' feedback during the same 22-second fixed-motor hold; all other motor references fixed.',
        physical_control_truth='Live simulation knife pose for middle support only; not a student deployment input.',
        scoring='Original gait-start world reference and 10mm/0.25rad threshold unchanged. Full 22-second gate, not only final second.',
        after_gate='Stop feedback preserving actual motor target; actual two-second settling; full frozen teacher if acquisition gate passes.')
    a.output.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='shadow'}))


if __name__=='__main__':main()
