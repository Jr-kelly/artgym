"""Declared rigid hand/knife roll, executed only through G2 motor targets.

One measured object pose defines the pivot and the complete desired object
trajectory before motion. The object stays free. Final hold and subsequent
gait use the fixed planned endpoint, never an updated measured reference.
"""
import json
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform


def plan_roll(k,command_start,object_start,degrees,seconds,dt,table_check):
    if abs(degrees)>45:raise ValueError('Bounded assembly roll exceeds45 degrees')
    start=k.forward(command_start);pivot=object_start[:3,3];axis=object_start[:3,2]
    previous=np.asarray(command_start).copy();motors=[];desired=[];errors=[]
    for i in range(round(seconds/dt)):
        u=(i+1)/round(seconds/dt);alpha=10*u**3-15*u**4+6*u**5
        r=Rotation.from_rotvec(axis*np.deg2rad(degrees)*alpha).as_matrix()
        wrist=start.copy();wrist[:3,:3]=r@start[:3,:3];wrist[:3,3]=pivot+r@(start[:3,3]-pivot)
        q,error=k.solve_near(wrist,previous,max_step=np.minimum(k.velocity*dt*.8,.15))
        collisions=table_check.collisions(q)
        if error['position_m']>.001 or error['rotation_rad']>.005 or collisions:
            raise ValueError('Assembly roll IK/clearance rejected: '+str(dict(frame=i,error=error,collisions=collisions)))
        reference=object_start.copy();reference[:3,:3]=r@object_start[:3,:3]
        motors.append(q);desired.append(reference);errors.append(error);previous=q
    return motors,desired,dict(axis_world=axis.tolist(),pivot_world=pivot.tolist(),degrees=degrees,
        seconds=seconds,arm_targets=[q.tolist() for q in motors],desired_object_world=[o.tolist() for o in desired],ik=errors,
        reference='One measured start, entire rigid trajectory fixed before motion. Object pose is never commanded.',
        target_gravity_in_knife_m_s2=(desired[-1][:3,:3].T@np.array([0,0,-9.81])).tolist())


def execute_roll(k,targets,arm_idx,current,tick,records,dt,table_check,output,degrees,seconds):
    _,_,_,w,o,_=current();relative=np.linalg.inv(w)@o;start=targets[arm_idx].copy()
    motors,desired,plan=plan_roll(k,start,o,degrees,seconds,dt,table_check)
    (output/'assembly-roll-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    first=len(records)
    for command in motors:
        targets[arm_idx]=command;tick('assembly_roll')
    count=len(motors)
    for _ in range(round(1./dt)):tick('assembly_roll_hold');desired.append(desired[-1].copy())
    rows=records[first:];refs=np.asarray(desired);objects=np.asarray([r['object'] for r in rows])
    dp=np.linalg.norm(objects[:,:3]-refs[:,:3,3],axis=1)
    dr=(Rotation.from_matrix(refs[:,:3,:3]).inv()*Rotation.from_quat(objects[:,3:])).magnitude()
    actual_relative=np.array([np.linalg.inv(transform(r['wrist'][:3],r['wrist'][3:]))@transform(r['object'][:3],r['object'][3:]) for r in rows])
    hp=np.linalg.norm(actual_relative[:,:3,3]-relative[:3,3],axis=1)
    hr=(Rotation.from_matrix(relative[:3,:3]).inv()*Rotation.from_matrix(actual_relative[:,:3,:3])).magnitude()
    lost=np.array([not np.any(r['finger_knife_contacts']) for r in rows])
    table=np.array([r['knife_table_contacts']>0 for r in rows])
    bad=(dp>=.01)|(dr>=.25)|(hp>=.01)|(hr>=.25)|lost|table
    raw_angle=(Rotation.from_matrix(o[:3,:3]).inv()*Rotation.from_quat(objects[:,3:])).magnitude()
    check=dict(success=bool(not bad.any()),frames=len(rows),first_instability_time_s=float(rows[np.flatnonzero(bad)[0]]['time']) if bad.any() else None,
        world_path_position_error_max_m=float(dp.max()),world_path_rotation_error_max_rad=float(dr.max()),
        hand_relative_position_error_max_m=float(hp.max()),hand_relative_rotation_error_max_rad=float(hr.max()),
        raw_world_rotation_from_roll_start_max_rad=float(raw_angle.max()),
        final_hold_position_error_max_m=float(dp[count:].max()),final_hold_rotation_error_max_rad=float(dr[count:].max()),
        first_motor_command_delta_rad=float(abs(motors[0]-start).max()),
        knife_table_frames=int(table.sum()),all_finger_contact_loss_frames=int(lost.sum()),
        final_planned_object_world=refs[-1].tolist(),planned_motion='Rigid assembly roll; raw world rotation is intentional, path errors remain10mm/0.25rad.',
        localization='One-time simulated object pose used for robot motor planning; oracle acquisition condition.')
    np.savez_compressed(output/'assembly-roll-reference.npz',time=np.array([r['time'] for r in rows]),desired_object_world=refs)
    (output/'assembly-roll-check.json').write_text(json.dumps(check,indent=2)+'\n')
    if bad.any():raise ValueError('Declared assembly roll/hold failed; see assembly-roll-check.json')
    return refs[-1]


def align_to_fixed_goal(k,targets,arm_idx,current,tick,records,dt,table_check,output,goal):
    """One small oracle orientation correction; the declared goal never moves."""
    _,_,_,_,actual,_=current();start=k.forward(targets[arm_idx]);pivot=actual[:3,3]
    correction=Rotation.from_matrix(goal[:3,:3]@actual[:3,:3].T).as_rotvec()
    if np.linalg.norm(correction)>.08 or np.linalg.norm(actual[:3,3]-goal[:3,3])>.005:
        raise ValueError('One-shot alignment outside declared small-error bounds')
    previous=targets[arm_idx].copy();commands=[]
    for i in range(round(1./dt)):
        u=(i+1)/round(1./dt);alpha=10*u**3-15*u**4+6*u**5
        r=Rotation.from_rotvec(correction*alpha).as_matrix();w=start.copy()
        w[:3,:3]=r@start[:3,:3];w[:3,3]=pivot+r@(start[:3,3]-pivot)
        q,error=k.solve_near(w,previous,max_step=np.minimum(k.velocity*dt*.8,.15))
        if error['position_m']>.001 or error['rotation_rad']>.005 or table_check.collisions(q):raise ValueError('Alignment IK rejected')
        commands.append(q);previous=q
    plan=dict(correction_world_rotvec=correction.tolist(),pivot_world=pivot.tolist(),unchanged_object_goal=goal.tolist(),
        arm_targets=[q.tolist() for q in commands],localization='One measured object orientation, robot motors only; simulation-truth control upper bound.')
    (output/'assembly-alignment-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    first=len(records)
    for q in commands:targets[arm_idx]=q;tick('assembly_align')
    for _ in range(round(1./dt)):tick('assembly_align_hold')
    rows=records[first:];obj=np.array([r['object'] for r in rows]);dp=np.linalg.norm(obj[:,:3]-goal[:3,3],axis=1)
    dr=(Rotation.from_matrix(goal[:3,:3]).inv()*Rotation.from_quat(obj[:,3:])).magnitude()
    bad=(dp>=.01)|(dr>=.25)|np.array([r['knife_table_contacts']>0 or not np.any(r['finger_knife_contacts']) for r in rows])
    check=dict(success=bool(not bad.any()),world_position_error_max_m=float(dp.max()),world_rotation_error_max_rad=float(dr.max()),
        final_position_error_m=float(dp[-1]),final_rotation_error_rad=float(dr[-1]),
        first_instability_time_s=float(rows[np.flatnonzero(bad)[0]]['time']) if bad.any() else None,
        unchanged_planned_reference=goal.tolist(),frames=len(rows))
    (output/'assembly-alignment-check.json').write_text(json.dumps(check,indent=2)+'\n')
    if bad.any():raise ValueError('Alignment to fixed roll goal failed')
