"""Offline posture-aware impedance preload along the known thumb path.

J(q)^T F/Kp gives nominal motor offsets, never measured/constant contact force.
Only calibrated geometry, prescribed path and known gains/limits enter. No
current slider/contact/resistance identifier is supplied at runtime.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_side_pickup_candidate import radius


def main():
    p=argparse.ArgumentParser();p.add_argument('--fit-issued-anchor',action='store_true',help='Fit initial nominalcontactwrench and nulltorque from knownclosedmotor target, then transportthroughposture Jacobians; actualpressure unknown');p.add_argument('--plan',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--project-collision',action='store_true',help='Constrain preload motor geometry while minimizing nominal contact-wrench change; independent actual force validation required');a=p.parse_args();assert not a.output.exists()
    plan=json.loads(a.plan.read_text());reference=json.loads(a.reference.read_text());g=DigitGeometry(knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;w=np.array(plan['wrist_in_knife']);normal=np.array(plan['contact_normals'][0]);q0=np.array(plan['touch_q']);force=np.array(plan['equilibrium_audit']['planned_force_on_knife_N'][0]);kp=np.array(OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').dof_props.stiffness)
    vertices=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);rows=[];previous=None;null_coefficient=0.;previous_null=None;anchor_audit=None
    def point(q):
        t=w@h.forward(q)['hand_r_thumb_pad_link'];v=vertices@t[:3,:3].T+t[:3,3];projection=v@normal;weights=np.exp(-(projection-projection.min())/.0002);return weights@v/weights.sum()
    for row in reference['rows']:
        q=q0.copy();q[16:]=row['q_thumb'];jac=np.empty((3,4))
        for j in range(4):
            delta=np.zeros(20);delta[16+j]=1e-5;jac[:,j]=(point(q+delta)-point(q-delta))/2e-5
        touch=np.array(row['q_thumb']);null=np.linalg.svd(jac.T,full_matrices=True)[0][:,-1]
        if previous_null is not None and null@previous_null<0:null=-null
        if a.fit_issued_anchor and not rows:
            initial_motor=np.array(plan['close_q'])[16:];initial_tau=kp[16:]*(initial_motor-touch);force=np.linalg.lstsq(jac.T,initial_tau,rcond=None)[0];null_coefficient=float(null@initial_tau);anchor_audit=dict(known_initial_motor=initial_motor.tolist(),nominal_linear_wrench_N=force.tolist(),null_torque_coefficient_Nm=null_coefficient,scope='Knownissuedtarget and calibratednominalcontactJacobian only; inferredforce isnot a force-sensor measurement')
        previous_null=null;preload=(jac.T@force+null*null_coefficient)/kp[16:];motor=touch+preload
        def geometry(x):
            full=np.array(plan['close_q']);full[16:]=x
            return np.array([r['gap_lower_bound_m'] for r in g.self_gaps(full,'thumb')+g.pair_gaps(full,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')])])
        nominal_motor=motor.copy();projected=None
        if a.project_collision and geometry(motor).min()<.000015:
            force_map=np.linalg.pinv(jac.T)
            def objective(x):
                inferred=force_map@(kp[16:]*(x-touch))
                return float(np.sum((inferred-force)**2)+.01*np.sum((x-nominal_motor)**2))
            lo=np.maximum(h.lower[16:]+.005,touch-.20);hi=np.minimum(h.upper[16:]-.005,touch+.20)
            if previous is not None:lo=np.maximum(lo,previous-.05);hi=np.minimum(hi,previous+.05)
            fit=minimize(objective,np.clip(motor,lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=lambda x:(geometry(x)-.000015)*1000)],options=dict(maxiter=80,ftol=1e-11));motor=fit.x
            projected=dict(optimizer_success=bool(fit.success),message=fit.message,minimum_constraint_m=float(geometry(motor).min()-.000015),nominal_motor_before_projection=nominal_motor.tolist(),estimated_force_after_projection_N=(force_map@(kp[16:]*(motor-touch))).tolist(),scope='Nominal linear contact-wrench estimate only; no measured force claim')
        full=np.array(plan['close_q']);full[16:]=motor
        limit_ok=bool(np.all(motor>=h.lower[16:]+.005-1e-7) and np.all(motor<=h.upper[16:]-.005+1e-7))
        self_rows=g.self_gaps(full,'thumb')+g.pair_gaps(full,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);frames=h.forward(full);bad=[]
        for candidate in self_rows:
            if candidate['gap_lower_bound_m']>0:continue
            names=[candidate.get('moving_link',candidate.get('link_a')),candidate.get('other_link',candidate.get('link_b'))]
            for va,_ in g.meshes[names[0]]:
                ta=frames[names[0]];va=va@ta[:3,:3].T+ta[:3,3]
                for vb,_ in g.meshes[names[1]]:
                    tb=frames[names[1]];vb=vb@tb[:3,:3].T+tb[:3,3];r=radius(va,vb)
                    if r is None or r>1e-5:bad.append(dict(pair=names,intersection_radius_m=r))
        r=dict(row,q_thumb_preloaded=motor.tolist(),nominal_joint_preload_rad=preload.tolist(),nominal_thumb_motor_tau_Nm=(jac.T@force).tolist(),collision_projection=projected,original_motor_limits_passed=limit_ok,self_intersections=bad,maximum_preloaded_joint_step_rad=float(abs(motor-previous).max()) if previous is not None else 0.);rows.append(r);previous=motor
    reference['rows']=rows;reference['issued_anchor_fit']=anchor_audit;reference['known_motor_anchor']=bool(a.fit_issued_anchor or reference.get('known_motor_anchor'));reference['posture_preload']=dict(scope=('Offline posture-Jacobian wrench/nulltorque transport from knownissuedinitialtarget; no measured/constantforce, resistanceID or currenttruth.' if a.fit_issued_anchor else 'Offline known-path Jacobian nominal motor preload, not measured/constant force. Same nominal thumb force vector as original static equilibrium, no resistance-ID or current truth input. Initial issued targets anchor the trajectory.'),planned_force_on_knife_N=force.tolist(),source_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),source_reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest())
    reference['motor_geometry_passed']=all(r['original_motor_limits_passed'] and not r['self_intersections'] for r in rows);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(reference,indent=2));print(json.dumps({'passed':reference['motor_geometry_passed'],'nominal_force_N':force.tolist(),'max_motor_step_rad':max(r['maximum_preloaded_joint_step_rad'] for r in rows),'offset_initial_rad':rows[0]['nominal_joint_preload_rad'],'offset_final_rad':rows[-1]['nominal_joint_preload_rad']}),flush=True);assert reference['motor_geometry_passed'],'Rejected motor preload reference; never execute'


if __name__=='__main__':main()
