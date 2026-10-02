"""Static contact-wrench motor targets, followed by actual physics validation.

This is a nominal impedance equilibrium, not measured or closed-loop force control.
Original hand gains/limits remain. Only offline calibrated geometry enters planning.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize,linprog
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--thumb-normal',type=float,default=1.5);p.add_argument('--joint-offset-limit',type=float,default=.20);p.add_argument('--friction',type=float,default=1.1);p.add_argument('--closed-slider-passive-limit',action='store_true',help='At lower mechanical stop, forbid unsupported positive thumb axial force that would pre-open a passive slider');p.add_argument('--table-margin',type=float,help='Optional nominal loaded motor-target/table separation in metres; independent swept-path audit still required');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    plan=json.loads(a.plan.read_text());g=DigitGeometry();h=g.w;q=np.asarray(plan['touch_q']);wrist=np.asarray(plan['wrist_in_knife']);normal=np.asarray(plan['contact_normals']);world=np.asarray(json.loads(a.calibration.read_text())['object_world_matrix'])
    def points(q):
        frames=h.forward(q);out=[]
        for f,n in zip(FINGERS,normal):
            mat=wrist@frames['hand_r_'+f+'_pad_link'];v=np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]);v=v@mat[:3,:3].T+mat[:3,3];proj=v@n;weights=np.exp(-(proj-proj.min())/.0002);weights/=weights.sum();out.append(weights@v)
        return np.asarray(out)
    active=[FINGERS.index(f) for f in plan.get('active_fingers',FINGERS)];normal=normal[active];count=len(active)
    # Contact extraction still uses the full mesh/name order.
    extraction_normals=np.asarray(plan['contact_normals'])
    def active_points(q):
        frames=h.forward(q);out=[]
        for index in active:
            f=FINGERS[index];n=extraction_normals[index];mat=wrist@frames['hand_r_'+f+'_pad_link'];v=np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]);v=v@mat[:3,:3].T+mat[:3,3];proj=v@n;weights=np.exp(-(proj-proj.min())/.0002);weights/=weights.sum();out.append(weights@v)
        return np.asarray(out)
    contact=active_points(q);jac=np.empty((count,3,20))
    for j in range(20):
        delta=np.zeros(20);delta[j]=1e-5;jac[:,:,j]=(active_points(q+delta)-active_points(q-delta))/2e-5
    profile=OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml');kp=np.asarray(profile.dof_props.stiffness)
    lower_offset=np.maximum(-a.joint_offset_limit,h.lower+.005-q)
    upper_offset=np.minimum(a.joint_offset_limit,h.upper-.005-q)
    gravity=world[:3,:3].T@np.array([0,0,-.035*9.81]);com=np.array([0,.0075,-.02205])*(.006/.035)
    preferred=np.array([a.thumb_normal]+[a.thumb_normal/(count-1)]*(count-1))
    slider_axial_upper=max(0.,float(-gravity[2]*(.006/.035)))+.001
    t1=np.array([np.eye(3)[np.argmin(abs(n))] for n in normal]);t2=np.cross(normal,t1)
    # Variables: normal magnitude plus two side-plane tangential components.
    def forces(x):return -normal*x[:,0:1]+t1*x[:,1:2]+t2*x[:,2:3]
    def equality(flat):
        f=forces(flat.reshape(count,3));return np.r_[f.sum(0)+gravity,np.cross(contact-com,f).sum(0)*100]
    def target_table_gaps(offset):
        target=q+offset;frames=h.forward(target);wrist_world=world@wrist;gaps=[]
        for name,meshes in g.meshes.items():
            mat=wrist_world@frames[name]
            for vertices,normals in meshes:
                v=vertices@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),normals@mat[:3,:3].T]
                proj=(v-np.array([.6,-.25,.725]))@axes.T;radius=abs(axes)@np.array([.3,.4,.025])
                gaps.append(float(np.maximum(proj.min(0)-radius,-radius-proj.max(0)).max()))
        return np.array(gaps)
    def inequality(flat):
        x=flat.reshape(count,3);offset=np.einsum('fij,fi->j',jac,forces(x))/kp
        constraints=np.r_[a.friction*x[:,0]-np.linalg.norm(x[:,1:],axis=1),offset-lower_offset,upper_offset-offset]
        if a.closed_slider_passive_limit:
            assert 0 in active
            constraints=np.r_[constraints,slider_axial_upper-forces(x)[active.index(0),2]]
        if a.table_margin is not None:
            constraints=np.r_[constraints,(target_table_gaps(offset)-a.table_margin)*100]
        return constraints
    seed=np.c_[preferred,-(t1@gravity)/count,-(t2@gravity)/count]
    fit=minimize(lambda x:float(((x.reshape(count,3)[:,0]-preferred)**2).sum()+.3*(x.reshape(count,3)[:,1:]**2).sum()),seed.ravel(),method='SLSQP',bounds=[b for _ in range(count) for b in [(0.08,3.),(-2.,2.),(-2.,2.)]],constraints=[dict(type='eq',fun=equality),dict(type='ineq',fun=inequality)],options=dict(maxiter=300,ftol=1e-12))
    linear_seed=None
    if not fit.success:
        # One conservative friction-pyramid feasibility solve supplies a valid
        # initial point for the existing quadratic/SOC optimization.
        zero=np.zeros(count*3);basis=np.eye(count*3)
        eq0=equality(zero);eqmatrix=np.stack([equality(v)-eq0 for v in basis],axis=-1)
        motor=np.stack([np.einsum('fij,fi->j',jac,forces(v.reshape(count,3)))/kp for v in basis],axis=-1)
        lhs=[motor,-motor];rhs=[upper_offset,-lower_offset]
        for finger in range(count):
            for tangent in [1,2]:
                for sign in [-1,1]:
                    row=np.zeros(count*3);row[finger*3]=-a.friction/np.sqrt(2);row[finger*3+tangent]=sign;lhs.append(row[None]);rhs.append(np.zeros(1))
        if a.closed_slider_passive_limit:
            axial=np.array([forces(v.reshape(count,3))[active.index(0),2] for v in basis]);lhs.append(axial[None]);rhs.append(np.array([slider_axial_upper]))
        lp=linprog(np.tile([1.,0.,0.],count),A_ub=np.concatenate(lhs),b_ub=np.concatenate(rhs),A_eq=eqmatrix,b_eq=-eq0,bounds=[b for _ in range(count) for b in [(0.08,3.),(-2.,2.),(-2.,2.)]],method='highs')
        linear_seed=dict(success=bool(lp.success),message=lp.message,scope='Conservative inner friction pyramid, geometry-only feasibility')
        if lp.success:
            fit=minimize(lambda x:float(((x.reshape(count,3)[:,0]-preferred)**2).sum()+.3*(x.reshape(count,3)[:,1:]**2).sum()),lp.x,method='SLSQP',bounds=[b for _ in range(count) for b in [(0.08,3.),(-2.,2.),(-2.,2.)]],constraints=[dict(type='eq',fun=equality),dict(type='ineq',fun=inequality)],options=dict(maxiter=300,ftol=1e-12))
    f=forces(fit.x.reshape(count,3));motor_tau=np.einsum('fij,fi->j',jac,f)
    offset=motor_tau/kp;bounded=np.clip(offset,-a.joint_offset_limit,a.joint_offset_limit);target=np.clip(q+bounded,h.lower+.005,h.upper-.005)
    plan['close_q']=target.tolist();plan['close_waypoints']=[dict(fraction=0.,q=plan['open_q']),dict(fraction=2/3,q=q.tolist()),dict(fraction=1.,q=target.tolist())]
    audit=dict(method='Static nominal impedance equilibrium; does not measure or regulate contact force',args=vars(a),optimizer_success=bool(fit.success),message=fit.message,contact_points_knife_m=contact.tolist(),planned_force_on_knife_N=f.tolist(),normal_N=fit.x.reshape(count,3)[:,0].tolist(),active_fingers=[FINGERS[i] for i in active],wrench_residual=equality(fit.x).tolist(),friction_assumption=a.friction,force_safety_margin=inequality(fit.x).tolist(),joint_offset_unbounded_rad=offset.tolist(),joint_offset_actual_rad=(target-q).tolist(),offset_clipped=bool(np.max(abs(offset-bounded))>1e-8),motor_tau_nominal_Nm=motor_tau.tolist(),no_hardware_calibration=True)
    plan['equilibrium_audit']=audit
    audit.update(linear_feasible_seed=linear_seed,closed_slider_positive_axial_force_upper_N=slider_axial_upper if a.closed_slider_passive_limit else None)
    if a.table_margin is not None:audit['nominal_loaded_target_minimum_table_gap_m']=float(target_table_gaps(target-q).min())
    (a.output/'motor-plan.json').write_text(json.dumps(plan,default=str,indent=2));(a.output/'audit.json').write_text(json.dumps(audit,default=str,indent=2));print(json.dumps(audit,default=str));assert fit.success and np.linalg.norm(equality(fit.x))<1e-4
if __name__=='__main__':main()
