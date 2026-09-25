"""Free-space wrist flip planning and measured retention diagnostics.

The object pose is read once to define a path pivot, never written. Paths contain
only G2 joint position targets. The physics runner retains full contact dynamics.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform


def plan_flip(k, wrist, obj, seed, degrees, seconds, dt, table_check, pivot_shift=(0.,0.,0.),axis_mode='wrist-forward'):
    axis = (wrist[:3, 2] if axis_mode=='wrist-forward' else obj[:3, 2]).copy()
    axis[2] = 0.
    if np.linalg.norm(axis) < .2:
        raise ValueError('Chosen flip axis has insufficient horizontal projection')
    axis /= np.linalg.norm(axis)
    pivot = obj[:3, 3].copy()
    start = np.asarray(seed, dtype=float).copy()
    path, errors, poses = [], [], []
    failure = None
    count = round(seconds / dt)
    for i in range(count):
        u = (i+1)/count
        alpha = 10*u**3 - 15*u**4 + 6*u**5
        r = Rotation.from_rotvec(axis*np.deg2rad(degrees)*alpha).as_matrix()
        target = wrist.copy()
        target[:3, :3] = r@wrist[:3, :3]
        target[:3, 3] = pivot + np.asarray(pivot_shift)*alpha + r@(wrist[:3, 3]-pivot)
        previous = path[-1] if path else start
        motor, error = k.solve_near(target, previous, max_step=np.minimum(k.velocity*dt*.8, .15))
        collisions = table_check.collisions(motor)
        errors.append(error)
        poses.append(target.tolist())
        if error['position_m'] > .003 or error['rotation_rad'] > .025 or collisions:
            failure = dict(control_frame=i, ik=error, arm_palm_table_collisions=collisions)
            break
        path.append(motor)
    diagnostic = dict(feasible=failure is None, failure=failure,
        method='One measured pivot and projected horizontal axis, smooth signed 180 degree rotation; continuous rate-limited G2 IK.',
        axis_mode=axis_mode,
        localization='One-time simulation truth at actual lift end; acquisition oracle baseline.',
        requested_degrees=degrees, duration_s=seconds, axis_world=axis.tolist(), pivot_world=pivot.tolist(),
        pivot_shift_world_m=list(pivot_shift),
        palm_normal_wrist=[1., 0., 0.], initial_palm_normal_world=wrist[:3, 0].tolist(),
        arm_targets=[q.tolist() for q in path], wrist_targets=poses, errors=errors,
        object_is_free=True, object_state_writes=False)
    return path, diagnostic


def check_flip(records, initial_wrist, initial_obj, table_height):
    objects=np.asarray([r['object'] for r in records]);wrists=np.asarray([r['wrist'] for r in records])
    relative=np.asarray([np.linalg.inv(transform(w[:3],w[3:]))@transform(o[:3],o[3:]) for w,o in zip(wrists,objects)])
    reference=np.linalg.inv(initial_wrist)@initial_obj
    drift=np.linalg.norm(relative[:,:3,3]-reference[:3,3],axis=1)
    angle=(Rotation.from_matrix(reference[:3,:3]).inv()*Rotation.from_matrix(relative[:,:3,:3])).magnitude()
    contact=np.asarray([r['finger_knife_contacts'] for r in records])>0
    no_contact=~contact.any(1)
    longest=length=0
    for lost in no_contact:
        length=length+1 if lost else 0;longest=max(longest,length)
    table_contacts=sum(r['knife_table_contacts'] for r in records)
    height=float(objects[:,2].min())
    retained=bool(height>table_height+.10 and table_contacts==0 and drift.max()<.025 and angle.max()<.35 and longest<=6)
    final=transform(wrists[-1,:3],wrists[-1,3:])
    return dict(retained=retained,frames=len(records),min_object_height_m=height,
        max_object_drift_in_hand_m=float(drift.max()),max_object_rotation_in_hand_rad=float(angle.max()),
        max_contact_loss_frames=longest,knife_table_contact_count=int(table_contacts),
        initial_palm_up_component=float(initial_wrist[2,0]),final_palm_up_component=float(final[2,0]),
        measured_wrist_rotation_deg=float(np.rad2deg(Rotation.from_matrix(initial_wrist[:3,:3].T@final[:3,:3]).magnitude())),
        thresholds=dict(min_height_m=table_height+.10,relative_drift_m=.025,relative_rotation_rad=.35,max_contact_loss_frames=6),
        qualification='Acquisition flip only, not functional grasp or policy success.')
