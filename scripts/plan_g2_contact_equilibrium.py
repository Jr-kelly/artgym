"""Static contact-wrench motor targets, followed by actual physics validation.

This is a nominal impedance equilibrium, not measured or closed-loop force control.
Original hand gains/limits remain. Only offline calibrated geometry enters planning.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--thumb-normal',type=float,default=1.5);p.add_argument('--joint-offset-limit',type=float,default=.20);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    plan=json.loads(a.plan.read_text());g=DigitGeometry();h=g.w;q=np.asarray(plan['touch_q']);wrist=np.asarray(plan['wrist_in_knife']);normal=np.asarray(plan['contact_normals']);world=np.asarray(json.loads(a.calibration.read_text())['object_world_matrix'])
    def points(q):
        frames=h.forward(q);out=[]
        for f,n in zip(FINGERS,normal):
            mat=wrist@frames['hand_r_'+f+'_pad_link'];v=np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]);v=v@mat[:3,:3].T+mat[:3,3];proj=v@n;weights=np.exp(-(proj-proj.min())/.0002);weights/=weights.sum();out.append(weights@v)
        return np.asarray(out)
    contact=points(q);jac=np.empty((5,3,20))
    for j in range(20):
        delta=np.zeros(20);delta[j]=1e-5;jac[:,:,j]=(points(q+delta)-points(q-delta))/2e-5
    profile=OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml');kp=np.asarray(profile.dof_props.stiffness)
    lower_offset=np.maximum(-a.joint_offset_limit,h.lower+.005-q)
    upper_offset=np.minimum(a.joint_offset_limit,h.upper-.005-q)
    gravity=world[:3,:3].T@np.array([0,0,-.035*9.81]);com=np.array([0,.0075,-.02205])*(.006/.035)
    preferred=np.array([a.thumb_normal]+[a.thumb_normal/4]*4)
    # Variables: normal magnitude plus two side-plane tangential components.
    def forces(x):return -normal*x[:,0:1]+np.c_[np.zeros(5),x[:,1],x[:,2]]
    def equality(flat):
        f=forces(flat.reshape(5,3));return np.r_[f.sum(0)+gravity,np.cross(contact-com,f).sum(0)*100]
    def inequality(flat):
        x=flat.reshape(5,3);offset=np.einsum('fij,fi->j',jac,forces(x))/kp
        return np.r_[1.1*x[:,0]-np.linalg.norm(x[:,1:],axis=1),offset-lower_offset,upper_offset-offset]
    seed=np.c_[preferred,np.tile(-gravity[1:]/5,(5,1))]
    fit=minimize(lambda x:float(((x.reshape(5,3)[:,0]-preferred)**2).sum()+.3*(x.reshape(5,3)[:,1:]**2).sum()),seed.ravel(),method='SLSQP',bounds=[b for _ in range(5) for b in [(0.08,3.),(-2.,2.),(-2.,2.)]],constraints=[dict(type='eq',fun=equality),dict(type='ineq',fun=inequality)],options=dict(maxiter=300,ftol=1e-12))
    f=forces(fit.x.reshape(5,3));motor_tau=np.einsum('fij,fi->j',jac,f)
    offset=motor_tau/kp;bounded=np.clip(offset,-a.joint_offset_limit,a.joint_offset_limit);target=np.clip(q+bounded,h.lower+.005,h.upper-.005)
    plan['close_q']=target.tolist();plan['close_waypoints']=[dict(fraction=0.,q=plan['open_q']),dict(fraction=2/3,q=q.tolist()),dict(fraction=1.,q=target.tolist())]
    audit=dict(method='Static nominal impedance equilibrium; does not measure or regulate contact force',args=vars(a),optimizer_success=bool(fit.success),message=fit.message,contact_points_knife_m=contact.tolist(),planned_force_on_knife_N=f.tolist(),normal_N=fit.x.reshape(5,3)[:,0].tolist(),wrench_residual=equality(fit.x).tolist(),friction_assumption=1.1,force_safety_margin=inequality(fit.x).tolist(),joint_offset_unbounded_rad=offset.tolist(),joint_offset_actual_rad=(target-q).tolist(),offset_clipped=bool(np.max(abs(offset-bounded))>1e-8),motor_tau_nominal_Nm=motor_tau.tolist(),no_hardware_calibration=True)
    plan['equilibrium_audit']=audit
    (a.output/'motor-plan.json').write_text(json.dumps(plan,default=str,indent=2));(a.output/'audit.json').write_text(json.dumps(audit,default=str,indent=2));print(json.dumps(audit,default=str));assert fit.success and np.linalg.norm(equality(fit.x))<1e-4
if __name__=='__main__':main()
