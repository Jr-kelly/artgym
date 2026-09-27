"""One-shot small-finger landing adaptation using explicitly privileged pose.

Keeps the original underside touch point and finite-drive closing displacement.
Only four small-finger targets change. No simulation handle, force or state write.
"""
import copy
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_seating_feedback import ContactCorrection
from scripts.audit_g2_wrist_plan import intersection_radius


def retarget(plan, measured_q, command_q, wrist, obj, slider):
    result=copy.deepcopy(plan);c=ContactCorrection();g=DigitGeometry()
    q=np.asarray(measured_q,dtype=float);command=np.asarray(command_q,dtype=float)
    relative=np.linalg.inv(obj)@wrist
    ids=np.arange(8,12);normals=np.array([[1.,0,0]]*5);normals[4]=[0,-1,0]
    geometry=plan['pinky_support_geometry'];solutions={};checks=[]
    for stage_name,original_key,point_key in [
        ('pinky_underside_touch','touch_q','target_point'),
        ('pinky_underside_close','command_q','close_target_point')]:
        old=np.asarray(geometry[original_key]);target=np.asarray(geometry[point_key])
        def point(v):
            state=q.copy();state[ids]=v
            return c.contacts(state,relative,normals)[0][4]
        solve=least_squares(lambda v:np.r_[(point(v)-target)*300,(v-old)*.005],old,
            bounds=(np.maximum(c.w.lower[ids],old-.12),np.minimum(c.w.upper[ids],old+.12)),
            max_nfev=100,diff_step=1e-5)
        error=float(np.linalg.norm(point(solve.x)-target))
        if error>.0005:raise ValueError('Small-finger adaptation IK residual exceeds0.5mm')
        solutions[stage_name]=solve.x
        checks.append(dict(stage=stage_name,original_point=point(old).tolist(),goal_point_in_knife=target.tolist(),
            planned_point=point(solve.x).tolist(),original_command=old.tolist(),adapted_command=solve.x.tolist(),
            maximum_change_rad=float(np.max(np.abs(solve.x-old))),geometric_error_m=error))
    pairs=[('hand_r_pinky_'+link,'hand_r_base_link') for link in ['link3','link4','pad_link']]
    pairs += [('hand_r_pinky_pad_link','hand_r_pinky_'+link) for link in ['link1','link2']]
    baseline=[intersection_radius(g,q,*pair) for pair in pairs]
    sweep=[];previous=command[ids].copy()
    for name in ['pinky_underside_touch','pinky_underside_close']:
        stage=next(s for s in result['stages'] if s['name']==name);goal=solutions[name]
        if 1.875*np.max(np.abs(goal-previous))/stage['seconds']>2:
            raise ValueError('Adapted small-finger motion exceeds original2rad/s planning bound')
        for alpha in np.linspace(0,1,21):
            state=q.copy();state[ids]=previous+(goal-previous)*alpha
            gap=g.minimum_gap(state,relative,slider,'pinky')
            selfgap=min(v['gap_lower_bound_m'] for v in g.self_gaps(state,'pinky'))
            # Same geometric contact allowances used by the original planner.
            allowance=-.00015 if name.endswith('touch') else -.0012
            overlap=[intersection_radius(g,state,*pair) for pair in pairs]
            passed=gap>=allowance and selfgap>=0 and all(v is not None and b is not None and v<=b+1e-5 for v,b in zip(overlap,baseline))
            sweep.append(dict(stage=name,alpha=float(alpha),knife_gap_m=gap,self_gap_m=selfgap,own_intersection_radii_m=overlap,passed=bool(passed)))
        stage['target']=goal.tolist();previous=goal.copy()
    diagnostic=dict(scope='One actual pose sample before small-finger touch; simulation-truth control upper bound',
        measured_q=q.tolist(),motor_reference=command.tolist(),wrist_in_knife=relative.tolist(),slider=slider,
        only_moving_indices=ids.tolist(),checks=checks,sweep=sweep,passed=all(v['passed'] for v in sweep),
        unchanged='other finger commands, wrist, durations, support/clearance gates, fixed world scoring, original physical limits',
        preload='Original planned underside touch -4.15mm and motor closure -3mm; nominal geometry is not a measured contact force')
    if not diagnostic['passed']:return None,diagnostic
    for stage in result['stages']:
        if 'required_initial_hand_command' not in stage:continue
        expected=np.asarray(stage['required_initial_hand_command'])
        if np.max(np.abs(expected[ids]-geometry['command_q']))>1e-6:
            raise ValueError('Unknown later small-finger reference; refuse implicit guard change')
        expected[ids]=previous;stage['required_initial_hand_command']=expected.tolist()
    return result,diagnostic
