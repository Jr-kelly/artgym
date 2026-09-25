"""G2 motor-only approach/lift path with continuous IK and table prechecks."""
import numpy as np
from scipy.spatial.transform import Rotation,Slerp


def plan_translation(k,seed,target,seconds,dt,table_check):
    seed=np.asarray(seed,dtype=float);start=k.forward(seed)
    rotations=Slerp([0.,1.],Rotation.from_matrix([start[:3,:3],target[:3,:3]]))
    path=[];errors=[];previous=seed.copy()
    for i in range(round(seconds/dt)):
        u=(i+1)/round(seconds/dt);alpha=10*u**3-15*u**4+6*u**5
        desired=np.eye(4);desired[:3,:3]=rotations([alpha]).as_matrix()[0]
        desired[:3,3]=start[:3,3]+alpha*(target[:3,3]-start[:3,3])
        q,error=k.solve_near(desired,previous,max_step=np.minimum(k.velocity*dt*.8,.15))
        collisions=table_check.collisions(q)
        if error['position_m']>.001 or error['rotation_rad']>.005 or collisions:
            raise ValueError('Cartesian acquisition precheck: '+str(dict(frame=i,error=error,collisions=collisions)))
        path.append(q);errors.append(error);previous=q
    return path,dict(method='Quintic Cartesian path, continuous bounded G2 IK, motor commands only',
        start_command=seed.tolist(),target_wrist=target.tolist(),arm_targets=[q.tolist() for q in path],errors=errors,
        duration_s=seconds,control_dt_s=dt,arm_palm_table_check=True)
