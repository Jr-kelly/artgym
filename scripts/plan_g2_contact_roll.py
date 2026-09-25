"""Small wrist motion with fixed contact locations, preceded by a single-digit gait.

This is not simultaneous contact interpolation: every selected contact point
and normal is frozen at the measured source pose. All joint changes compensate
for the moving finger bases. Motor offsets are measured command-minus-position,
not force observations. Only a physical trial can verify maintained contacts.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import G2Kinematics,transform,ROOT
from scripts.g2_seating_feedback import ContactCorrection


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prefix-plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--degrees',type=float,default=5.)
    p.add_argument('--adjust-translation',action='store_true',help='Allow up to 10mm wrist translation to preserve fixed contacts; knife reference remains fixed.')
    a=p.parse_args();c=ContactCorrection();w=c.w;k=G2Kinematics();plan=json.loads(a.prefix_plan.read_text())
    d=json.loads(a.source.read_text());trial=Path(d['source_trial']);t=np.load(trial/'trace.npz');i=d['source_step']
    obj=transform(t['object'][i,:3],t['object'][i,3:]);arm=t['arm_q'][i].astype(float)
    q=np.asarray(d['touch_q']);command=np.asarray(d['close_q']);offset=command-q;relative=np.asarray(d['wrist_in_knife'])
    normals=np.asarray(d['contact_normals']);points=c.contacts(q,relative,normals)[0]
    cache=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    final=np.linalg.inv(transform(cache[40:43],cache[43:47]));angle=Rotation.from_matrix(relative[:3,:3].T@final[:3,:3]).magnitude()
    alpha=min(np.deg2rad(a.degrees)/angle,1);slerp=Slerp([0,1],Rotation.from_matrix([relative[:3,:3],final[:3,:3]]))
    diagnostics=[]
    for j in range(1,round(a.degrees)+1):
        fraction=alpha*j/round(a.degrees);rel=relative.copy();rel[:3,:3]=slerp([fraction]).as_matrix()[0]
        rel[:3,3]=relative[:3,3]*(1-fraction)+final[:3,3]*fraction
        def residual(v):
            actual=rel.copy()
            if a.adjust_translation:actual[:3,3]+=v[:3];v=v[3:]
            errors=np.r_[(c.contacts(v,actual,normals)[0]-points).ravel()*200,(v-q)*.03]
            return errors
        seed=np.r_[np.zeros(3),q] if a.adjust_translation else q
        lo=np.r_[np.full(3,-.01),w.lower] if a.adjust_translation else w.lower
        hi=np.r_[np.full(3,.01),w.upper] if a.adjust_translation else w.upper
        result=least_squares(residual,np.clip(seed,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=120,diff_step=1e-5)
        error=np.linalg.norm(residual(result.x)[:15].reshape(5,3)/200,axis=1)
        if error.max()>.001:raise ValueError('Contact-preserving IK infeasible '+str((j,error)))
        q=result.x[-20:]
        if a.adjust_translation:rel[:3,3]+=result.x[:3]
        motor=np.clip(q+offset,w.lower,w.upper);arm,ik=k.solve_near(obj@rel,arm)
        if ik['position_m']>.001 or ik['rotation_rad']>.005:raise ValueError('Arm IK infeasible '+str(ik))
        plan['stages'].append(dict(name='contact_roll_'+str(j),kind='contact_preserving_wrist_motion',moving_indices=list(range(20)),target=motor.tolist(),arm_target=arm.tolist(),seconds=1.))
        diagnostics.append(dict(degrees=j,errors_m=error.tolist(),ik=ik,wrist_in_object=rel.tolist()))
    plan['stages'].append(dict(name='rolled_support_hold',kind='hold',seconds=1.))
    plan['contact_roll']=dict(source=str(a.source),degrees=a.degrees,fixed_points=points.tolist(),fixed_normals=normals.tolist(),
        measured_motor_offsets=offset.tolist(),diagnostics=diagnostics,method=__doc__)
    a.output.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),degrees=a.degrees)))


if __name__=='__main__':main()
