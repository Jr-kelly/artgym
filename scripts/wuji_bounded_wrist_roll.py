"""Small motor-only wrist roll from once-known arm/FK and grip calibration.

The curve rotates about the estimated knife long axis at a fixed wrist origin.
It accepts no current object, contact, slider or resistance state. Actual arm
motion still comes from the runner's original finite-torque motors.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics


def plan_curve(nominal_q, object_in_wrist, maximum_degrees=4., count=17):
    assert 0 < maximum_degrees <= 4 and count >= 3 and count % 2 == 1
    kin=G2Kinematics();nominal_q=np.asarray(nominal_q,dtype=float)
    nominal=kin.forward(nominal_q)
    axis=nominal[:3,:3]@np.asarray(object_in_wrist)[:3,2]
    axis/=np.linalg.norm(axis)
    shifts=np.linspace(-np.deg2rad(maximum_degrees),np.deg2rad(maximum_degrees),count)
    rows=[None]*count;center=count//2;rows[center]=nominal_q.tolist();errors=[]
    for indices in [range(center+1,count),range(center-1,-1,-1)]:
        seed=nominal_q.copy()
        for index in indices:
            target=nominal.copy()
            target[:3,:3]=Rotation.from_rotvec(axis*shifts[index]).as_matrix()@nominal[:3,:3]
            seed,audit=kin.solve_near(target,seed,max_step=.25)
            assert audit['position_m']<.00025 and audit['rotation_rad']<.001,audit
            rows[index]=seed.tolist();errors.append(audit)
    q=np.asarray(rows)
    maximum_joint_change=float(np.abs(q-nominal_q).max())
    assert maximum_joint_change<.25
    return dict(roll_rad=shifts.tolist(),arm_q=q.tolist(),nominal_arm_q=nominal_q.tolist(),
        maximum_joint_change_rad=maximum_joint_change,IK=errors,
        axis_world_from_known_estimate=axis.tolist(),
        scope='Known FK/once-initial grip calibration only; offline IK, not a collision/force certificate. Original motors/gravity/effort retained; no object attachment.')


def interpolate(curve,roll_rad):
    shifts=np.asarray(curve['roll_rad']);q=np.asarray(curve['arm_q'])
    assert shifts[0]-1e-8<=roll_rad<=shifts[-1]+1e-8
    return np.array([np.interp(roll_rad,shifts,q[:,i]) for i in range(7)])
