"""Offline support-load redistribution from known planned thumb motion.

This is a bounded motor feedforward profile, not force control. Its nominal
wrench preference is never presented as an actual contact force. No physical
asset or live object/contact state is read.
"""
import copy
import numpy as np
from scipy.optimize import minimize
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS


def adapt_stroke_support(plan, reference, preload_scale=1.25, offset_bound=.025):
    g=DigitGeometry();h=g.w;touch=np.asarray(plan['touch_q'])
    wrist=np.asarray(plan['wrist_in_knife']);normals=np.asarray(plan['contact_normals'])
    supports=['index','middle','pinky'];indices=[FINGERS.index(f) for f in supports]
    audit=plan['equilibrium_audit'];names=audit['active_fingers']
    baseline=np.asarray([audit['normal_N'][names.index(f)] for f in supports])*preload_scale
    thumb_normal=float(audit['normal_N'][names.index('thumb')])*preload_scale
    kp=np.asarray(OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').dof_props.stiffness)

    def point(q,f):
        i=FINGERS.index(f);frame=wrist@h.forward(q)['hand_r_'+f+'_pad_link']
        vertices=np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']])@frame[:3,:3].T+frame[:3,3]
        p=vertices@normals[i];w=np.exp(-(p-p.min())/.0002);w/=w.sum()
        return w@vertices

    positions=np.asarray([point(touch,f) for f in supports]);forces=-normals[indices]
    # Only the change in planned thumb moment is redistributed. Total support
    # normal preference is fixed; this does not increase global squeeze.
    moment=np.cross(positions,forces).T
    jac=np.zeros((3,3,20))
    for j in range(16):
        delta=np.zeros(20);delta[j]=1e-5
        for i,f in enumerate(supports):jac[i,:,j]=(point(touch+delta,f)-point(touch-delta,f))/2e-5
    first=touch.copy();first[16:]=reference['rows'][0]['q_thumb'];origin=point(first,'thumb')
    out=copy.deepcopy(reference);rows=[]
    for row in out['rows']:
        q=touch.copy();q[16:]=row['q_thumb']
        desired_moment=-np.cross(point(q,'thumb')-origin,-normals[0]*thumb_normal)
        fit=minimize(lambda load:float(np.sum((100*(moment@(load-baseline)-desired_moment))**2)+.01*np.sum((load-baseline)**2)),baseline,
                     method='SLSQP',bounds=[(.06,1.2)]*3,
                     constraints=[dict(type='eq',fun=lambda load:load.sum()-baseline.sum())],
                     options=dict(maxiter=100,ftol=1e-12))
        if not fit.success:raise RuntimeError('Support redistribution optimization: '+fit.message)
        change=forces*(fit.x-baseline)[:,None]
        offset=np.einsum('fij,fi->j',jac,change)/kp
        bounded=np.clip(offset[:16],-offset_bound,offset_bound)
        row['support_offset_rad']=bounded.tolist()
        rows.append(dict(shift_m=row['shift_m'],nominal_support_normal_N=fit.x.tolist(),
                         desired_moment_change_Nm=desired_moment.tolist(),
                         model_moment_residual_Nm=(moment@(fit.x-baseline)-desired_moment).tolist(),
                         maximum_motor_offset_rad=float(abs(bounded).max()),
                         clipped=bool(np.max(abs(offset[:16]-bounded))>1e-9)))
    out['stroke_support_scope']='Known scheduled thumb-path wrench preference redistributed among three existing support digits; bounded motor feedforward, original limits/finite PD; no actual force or current object feedback.'
    return out,dict(scope=out['stroke_support_scope'],nominal_thumb_normal_N=thumb_normal,
                    nominal_support_baseline_N=baseline.tolist(),offset_bound_rad=offset_bound,
                    actual_contact_force_unverified=True,rows=rows)
