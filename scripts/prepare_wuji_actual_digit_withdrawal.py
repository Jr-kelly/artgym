"""Withdraw an entire loaded digit using its actual geometry and issued preload.

Other digits and wrist retain their issued motor commands. This plans a free
digit, not a held spatial constraint. Native support must be checked next.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for key in ['source','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--finger',default='middle');p.add_argument('--clearance-m',type=float,default=.002)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float);issued=s['issued_target'][7:].astype(float)
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();W=k.forward(s['robot_q'][:7]);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@W
    ids=np.array([g.w.names.index('hand_r_'+a.finger+'_joint'+str(j)) for j in range(1,5)]);initial=g.gaps(q0,L,float(s['slider_q']),a.finger)
    initial_self={(v['moving_link'],v['other_link']):v['gap_lower_bound_m'] for v in g.self_gaps(q0,a.finger,certify_clearance_m=.0005)}
    lo=np.maximum(g.w.lower[ids]+.06,q0[ids]-.6);hi=np.minimum(g.w.upper[ids]-.06,q0[ids]+.6)
    rows=[];D=[];c=HandIntersection();previous=q0[ids].copy()
    record('actual_whole_digit_withdrawal_start',[str(a.output)],config={'source':str(a.source),'finger':a.finger,'clearance_m':a.clearance_m,'uncertainty':'Single middle3 opening leaves actual middle contact; can complete actual digit withdraw while all other issued clamp commands remain?','decision':'Native wholly-free middle supports two-carrier transfer; lostclamp -> acquire other support before middle withdrawal'},next_step='Whole digit geometry ramp, original dynamics then one actual support test')
    for t in np.linspace(0,4,33):
        u=smooth(t/2.5)
        def decode(x):
            h=q0.copy();h[ids]=x;return h
        def constraints(x):
            h=decode(x);values=[v['gap_lower_bound_m']-((1-u)*min(a.clearance_m,old['gap_lower_bound_m'])+u*a.clearance_m) for v,old in zip(g.gaps(h,L,float(s['slider_q']),a.finger),initial)]
            values.extend(v['gap_lower_bound_m']-((1-u)*min(.0005,initial_self[v['moving_link'],v['other_link']])+u*.0005) for v in g.self_gaps(h,a.finger,certify_clearance_m=.0005))
            F=g.w.forward(h)
            values.extend(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.751) for n,parts in g.meshes.items() if '_'+a.finger+'_' in n for v,_ in parts)
            return np.array(values)
        if u>0:
            fit=minimize(lambda x:float(np.sum((x-q0[ids])**2)),previous,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=80,ftol=1e-11))
            previous=fit.x
        h=decode(previous);command=issued.copy();command[ids]=h[ids]+(issued[ids]-q0[ids])*(1-u)
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=command.tolist()))
        D.append(dict(time_s=float(t),self=c.inspect(h),minimum_constraint_m=float(constraints(previous).min()),planned_hand_q=h.tolist(),digit_gap_m=min(v['gap_lower_bound_m'] for v in g.gaps(h,L,float(s['slider_q']),a.finger))))
        if D[-1]['minimum_constraint_m']<-.00005 or D[-1]['self']:break
    guard=dict(complete=len(D)==33,self_frames=sum(bool(d['self']) for d in D),minimum_constraint_m=min(d['minimum_constraint_m'] for d in D),terminal_digit_gap_m=D[-1]['digit_gap_m'],source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()))
    guard['preflight_pass']=guard['complete'] and not guard['self_frames'] and guard['minimum_constraint_m']>-.00005 and guard['terminal_digit_gap_m']>a.clearance_m-.00001
    out=dict(rows=rows,diagnostics=D,guard=guard,source=str(a.source),development_abort_on_translation_m=.015,scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(out,indent=2));print(json.dumps(guard),flush=True)
    e=record('actual_whole_digit_withdrawal_terminal',[str(a.output/'motor.json')],config=guard,next_step='Passing path -> native4s actual retained-clamp test')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(guard)+'\n')
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
