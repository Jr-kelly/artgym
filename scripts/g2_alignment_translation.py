"""One bounded physical translation to satisfy the unchanged alignment gate."""
import json
import numpy as np
from scipy.spatial.transform import Rotation


def translate_toward_fixed_goal(k,targets,arm_idx,current,tick,records,dt,table_check,output,goal):
    from scripts.audit_g2_self_clearance import Clearance
    _,_,_,_,actual,_=current()
    offset=goal[:3,3]-actual[:3,3];distance=float(np.linalg.norm(offset))
    angle=float(Rotation.from_matrix(goal[:3,:3]@actual[:3,:3].T).magnitude())
    if distance<=.005:
        (output/'translation-plan.json').write_text(json.dumps(dict(executed=False,reason='original5mm gate already satisfied'))+'\n')
        return
    if distance>=.01 or angle>=.25:
        raise ValueError('Translation start violates unchanged gait stability bounds')
    delta=offset*min(1.,.004/distance)
    start=k.forward(targets[arm_idx]);previous=targets[arm_idx].copy()
    checks=Clearance();commands=[];knife_path=[]
    for i in range(round(1./dt)):
        u=(i+1)/round(1./dt);alpha=10*u**3-15*u**4+6*u**5
        wrist=start.copy();wrist[:3,3]+=delta*alpha
        q,error=k.solve_near(wrist,previous,max_step=np.minimum(k.velocity*dt*.8,.15))
        if error['position_m']>.001 or error['rotation_rad']>.005 or table_check.collisions(q) or checks.collisions(q):
            raise ValueError('Translation IK/collision precheck rejected')
        commands.append(q.copy());previous=q
        knife=actual.copy();knife[:3,3]+=delta*alpha;knife_path.append(knife)
    plan=dict(executed=True,translation_cap_m=.004,move_seconds=1.,hold_seconds=1.,
        initial_object=actual.tolist(),translation=delta.tolist(),unchanged_world_goal=goal.tolist(),
        expected_object_trajectory=[p.tolist() for p in knife_path],arm_targets=[q.tolist() for q in commands],
        localization='one actual simulated object position; motor planning upper bound',
        reference='original gait world goal never changes; planned knife motion recorded before physics',
        following_alignment_gate='original5mm position and .25rad orientation gates unchanged')
    (output/'translation-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    first=len(records)
    for q in commands:targets[arm_idx]=q;tick('assembly_translate')
    for _ in range(round(1./dt)):tick('assembly_translate_hold')
    rows=records[first:];objects=np.array([r['object'] for r in rows])
    expected=np.stack(knife_path+[knife_path[-1]]*round(1./dt))
    dp=np.linalg.norm(objects[:,:3]-goal[:3,3],axis=-1)
    dr=(Rotation.from_matrix(goal[:3,:3]).inv()*Rotation.from_quat(objects[:,3:])).magnitude()
    tracking=np.linalg.norm(objects[:,:3]-expected[:,:3,3],axis=-1)
    tracking_rotation=(Rotation.from_matrix(actual[:3,:3]).inv()*Rotation.from_quat(objects[:,3:])).magnitude()
    invalid=(dp>=.01)|(dr>=.25)|(tracking>=.01)|(tracking_rotation>=.25)|np.array([r['knife_table_contacts']>0 or not np.any(r['finger_knife_contacts']) for r in rows])
    contacts=np.mean(np.array([r['finger_knife_contacts'] for r in rows[-round(1./dt):]])>0,axis=0)
    required=bool(np.all(contacts[[0,2,3]]>=.9))
    result=dict(success=bool(not invalid.any() and required),fixed_world_position_max_m=float(dp.max()),
        fixed_world_rotation_max_rad=float(dr.max()),planned_tracking_error_max_m=float(tracking.max()),
        planned_tracking_rotation_max_rad=float(tracking_rotation.max()),final_position_error_m=float(dp[-1]),
        support_hold_contact_fraction=contacts.tolist(),required_support_held=required,
        first_instability_world_s=float(rows[np.flatnonzero(invalid)[0]]['time']) if invalid.any() else None,
        fixed_reference=goal.tolist(),frames=len(rows))
    (output/'translation-check.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['success']:raise ValueError('Physical translation failed unchanged stability/support checks')
