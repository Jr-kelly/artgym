"""Rigidly retarget an existing wrist motor path at the real gait boundary.

Robot-command geometry only. Hand targets, fixed object success reference,
servo, limits and physical state are unchanged. Not a contact controller.
"""
import copy
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_table_collision import ArmTableCollision


def retarget(plan, nominal_start, actual_start, table_height):
    k=G2Kinematics();collision=ArmTableCollision(table_height)
    nominal_start=np.asarray(nominal_start);actual_start=np.asarray(actual_start)
    delta=k.forward(actual_start)@np.linalg.inv(k.forward(nominal_start))
    result=copy.deepcopy(plan);q=actual_start.copy();checks=[]
    identity=bool(np.max(np.abs(actual_start-nominal_start))<1e-7)
    for stage in result['stages']:
        if 'arm_target' not in stage:continue
        original=np.array(stage['arm_target']);target=delta@k.forward(original)
        if identity:
            new=original.copy();error=dict(position_m=0.,rotation_rad=0.,joint_margin_rad=float(np.minimum(new-k.lower,k.upper-new).min()))
        else:
            new,error=k.solve_near(target,q)
        if error['position_m']>.001 or error['rotation_rad']>.005:
            raise ValueError('Retargeted gait IK precheck failed: '+str((stage['name'],error)))
        for u in np.linspace(0,1,11):
            test=q+(new-q)*(10*u**3-15*u**4+6*u**5)
            hits=collision.collisions(test)
            if hits:raise ValueError('Retargeted arm/table precheck: '+str((stage['name'],u,hits)))
        seconds=stage.get('seconds',1.)
        if np.any(1.875*np.abs(new-q)/seconds>k.velocity):
            raise ValueError('Retargeted arm velocity above original asset limit')
        checks.append(dict(stage=stage['name'],ik=error,
            original_arm_target=original.tolist(),retargeted_arm_target=new.tolist(),
            transformed_wrist_goal=target.tolist(),max_joint_step_rad=float(np.max(np.abs(new-q)))))
        stage['arm_target']=new.tolist();q=new
    evidence=dict(method='constant world transform of original commanded wrist path, sequential same-branch IK',
        input_source='actual motor reference at gait boundary, nominal reference from successful prefix',
        nominal_start=nominal_start.tolist(),actual_start=actual_start.tolist(),world_transform=delta.tolist(),
        wrist_origin_displacement_m=float(np.linalg.norm(k.forward(actual_start)[:3,3]-k.forward(nominal_start)[:3,3])),
        transform_translation_caution='World transform translation includes rotation lever arm; not knife motion inside hand',
        nominal_identity_preserved=identity,geometric_checks=checks,
        unchanged='hand motor plan, stage timing/gates, fixed gait object reference, physics',
        qualification='geometric precheck, not holding or operation evidence')
    return result,evidence
