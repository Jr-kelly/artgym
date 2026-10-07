"""Retain an acquired carrier using measured joints and explicit knife pose.

The captured joint-deflection wrench is a proxy, not a force measurement.
Native contacts remain evaluation-only. All outputs are finite motor targets.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_direct_pickup import smooth


class DirectMaterialCarrier:
    def __init__(self, spec, output):
        self.s = spec
        self.g = DigitGeometry(max_face_axes=10, knife_spec=Path(spec['knife_spec']))
        self.k = G2Kinematics()
        self.ids = np.array(spec['digit_indices'], dtype=int)
        self.name = spec['material_link']
        self.finger = self.name.split('_')[2]
        self.material = np.array(spec['material_point'])
        self.kp = np.array(spec['digit_kp'])
        self.capture = None
        self.position_correction=np.zeros(len(self.ids))
        self.log = Path(output)/'direct-material-carrier.jsonl'

    def correct(self, t, O, arm, hand, issued_hand, reference_hand, slider):
        actual_L = np.linalg.inv(O) @ self.k.forward(arm)
        # Once the free thumb crosses above the cap, retain the observed
        # world pose as a motor reference. Following a knife pushed by the
        # thumb would unload the carriers instead of providing a reaction.
        hold_start=self.s.get('world_hold_start_s')
        if hold_start is not None and t>=hold_start and not hasattr(self,'hold_pose'):
            self.hold_pose=O.copy()
            self.hold_pose_origin=O.copy()
        translation_path=self.s.get('world_translation_path')
        if translation_path and hasattr(self,'hold_pose'):
            # A lift transports the captured reaction frame along its known
            # motor path. It must never chase the observed slipping knife.
            times=np.array([row['time_s'] for row in translation_path])
            delta=np.array([np.interp(t,times,[row['translation_m'][j] for row in translation_path]) for j in range(3)])
            self.hold_pose=self.hold_pose_origin.copy()
            self.hold_pose[:3,3]+=delta
        L=np.linalg.inv(self.hold_pose)@self.k.forward(arm) if hasattr(self,'hold_pose') else actual_L
        q = hand.astype(float)
        path=self.s.get('material_path')
        if path:
            times=np.array([row['time_s'] for row in path])
            self.material=np.array([np.interp(t,times,[row['material_point'][j] for row in path]) for j in range(3)])

        def point(h,frame=None):
            T = (L if frame is None else frame) @ self.g.w.forward(h)[self.name]
            return T[:3, :3] @ self.material + T[:3, 3]

        def jacobian(h):
            P = point(h)
            J = np.empty((3, 4))
            for j, index in enumerate(self.ids):
                hh = h.copy(); hh[index] += 1e-5
                J[:, j] = (point(hh)-P)/1e-5
            return J

        if self.capture is None:
            J = jacobian(q)
            tau = self.kp*(issued_hand[self.ids]-q[self.ids])
            force = np.linalg.solve(J @ J.T+np.eye(3)*1e-7, J @ tau)
            if self.s.get('add_world_up_reference_N') is not None:
                force+=O[:3,:3].T@np.array([0.,0.,float(self.s['add_world_up_reference_N'])])
            self.capture = dict(point=point(q), force=force,
                                # Keep the original null torque; the added
                                # known weight must remain in the feedforward.
                                null_tau=tau-J.T @ (force-O[:3,:3].T@np.array([0.,0.,float(self.s.get('add_world_up_reference_N',0.))])), hand=q.copy(), issued_hand=issued_hand.copy())
            if self.s.get('preserve_acquired_body_gaps'):
                # A link can have several collision parts. Preserve each
                # part separately; a link-pair dictionary loses its deep part
                # when a later, separated part has the same link names.
                self.initial_gaps=[v['gap_lower_bound_m']
                                   for v in self.g.gaps(q,L,slider,self.finger)]
        target = self.capture['point']
        margin = self.s.get('planning_margin_rad', .06)
        lower = self.g.w.lower[self.ids]+margin
        upper = self.g.w.upper[self.ids]-margin
        for index in self.s.get('fixed_planning_joint_indices',[]):
            j=list(self.ids).index(index)
            lower[j]=max(lower[j],self.capture['hand'][index]-.005)
            upper[j]=min(upper[j],self.capture['hand'][index]+.005)
        prior = np.clip(reference_hand[self.ids], lower, upper)

        def residual(x):
            h = q.copy(); h[self.ids] = x
            r = list((point(h)-target)*350)
            r.extend((x-prior)*.025)
            for part_index,gap in enumerate(self.g.gaps(h, L, slider, self.finger)):
                threshold = (-.00015 if gap['hand_link']==self.name
                             and gap['knife_link']=='link_0' else .0001)
                if self.s.get('preserve_acquired_body_gaps'):
                    threshold=min(threshold,self.initial_gaps[part_index])
                r.append(min(0, gap['gap_lower_bound_m']-threshold)*500)
            r.extend(min(0, gap['gap_lower_bound_m']-.0001)*150
                     for gap in self.g.self_gaps(h, self.finger,
                                                certify_clearance_m=.0001))
            return np.array(r)

        fit = least_squares(residual, np.clip(q[self.ids], lower, upper),
                            bounds=(lower, upper), max_nfev=25, diff_step=1e-5)
        ref = q.copy(); ref[self.ids] = fit.x
        J = jacobian(ref)
        # Transport the same acquired proxy wrench through the current
        # Jacobian, instead of preserving an old joint offset as the wrist turns.
        preload = (J.T @ self.capture['force']+self.capture['null_tau'])/self.kp
        damping_lead=np.zeros(4)
        if 'digit_kd' in self.s:
            if hasattr(self,'last_fit') and t>self.last_fit_time:
                velocity=(fit.x-self.last_fit)/(t-self.last_fit_time)
                bound=self.s.get('max_damping_lead_rad',.07)
                damping_lead=np.clip(np.array(self.s['digit_kd'])/self.kp*velocity,-bound,bound)
            self.last_fit=fit.x.copy();self.last_fit_time=float(t)
        position_servo=self.s.get('world_position_servo')
        if position_servo:
            if not hasattr(self,'hold_pose'):
                raise ValueError('World reaction position servo requires a captured world pose')
            measured_J=jacobian(q)
            for index in self.s.get('fixed_motor_joint_indices',[]):
                measured_J[:,list(self.ids).index(index)]=0.
            error=target-point(q)
            if position_servo.get('feedback_coordinates') in ['fit_joint','fit_joint_tangential']:
                # A curled digit can be close to a point-Jacobian branch
                # singularity. Follow the bounded collision-aware IK branch
                # already chosen above instead of inverting that Jacobian.
                delta=fit.x-q[self.ids]
                if position_servo.get('feedback_coordinates')=='fit_joint_tangential':
                    # Material tracking must not integrate away the loaded
                    # side-normal deflection that supplies the clamp force.
                    normal=np.asarray(self.s['contact_normal_knife'],dtype=float)
                    normal=normal/np.linalg.norm(normal)
                    normal_row=normal@measured_J
                    delta-=normal_row*(normal_row@delta)/(normal_row@normal_row+1e-10)
            else:
                delta=measured_J.T@np.linalg.solve(measured_J@measured_J.T+np.eye(3)*1e-7,error)
            delta*=position_servo['gain']*smooth(t/.3)
            delta=np.clip(delta,-position_servo['max_step_rad'],position_servo['max_step_rad'])
            for index in self.s.get('fixed_motor_joint_indices',[]):
                delta[list(self.ids).index(index)]=0.
            self.position_correction=np.clip(self.position_correction+delta,
                -position_servo['max_correction_rad'],position_servo['max_correction_rad'])
        bound=self.s.get('max_preload_rad',.1)
        loaded=fit.x+np.clip(preload, -bound, bound)+damping_lead
        desired = loaded+self.position_correction
        desired = np.clip(desired, self.g.w.lower[self.ids]+.02,
                          self.g.w.upper[self.ids]-.02)
        command = reference_hand.copy()
        max_step = self.s.get('max_step_rad', .02)
        command[self.ids] = issued_hand[self.ids]+np.clip(
            (desired-issued_hand[self.ids])*smooth(t/.3), -max_step, max_step)
        for index in self.s.get('fixed_motor_joint_indices',[]):
            command[index]=self.capture['issued_hand'][index]
        for index,margin in self.s.get('command_upper_margins_rad',{}).items():
            index=int(index);command[index]=min(command[index],self.g.w.upper[index]-margin)
        if position_servo:
            # Do not integrate beyond physical target bounds, reserve caps or
            # the existing issued-target slew bound.
            self.position_correction=np.clip(command[self.ids]-loaded,
                -position_servo['max_correction_rad'],position_servo['max_correction_rad'])
            for index in self.s.get('fixed_motor_joint_indices',[]):
                self.position_correction[list(self.ids).index(index)]=0.
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t), material_link=self.name,
                target_material_knife_m=target.tolist(),
                material_point_local_m=self.material.tolist(),
                actual_digit_q=q[self.ids].tolist(),
                fitted_digit_q=fit.x.tolist(),
                world_position_correction_rad=self.position_correction.tolist(),
                actual_material_knife_m=point(q,actual_L).tolist(),
                actual_material_error_m=float(np.linalg.norm(point(q,actual_L)-target)),
                controlled_material_error_m=float(np.linalg.norm(point(q)-target)),
                fit_material_error_m=float(np.linalg.norm(point(ref)-target)),
                captured_joint_deflection_wrench_proxy_N=self.capture['force'].tolist(),
                transported_preload_rad=preload.tolist(),
                bounded_original_damping_velocity_lead_rad=damping_lead.tolist(),
                world_pose_hold_active=hasattr(self,'hold_pose'),
                motor_reference_object_world=self.hold_pose.tolist() if hasattr(self,'hold_pose') else None,
                issued_digit_q=command[self.ids].tolist(),
                pose_source='sim_oracle explicit pose plus measured joints/history',
                scope='No nativecontact/force input or physicalstate writes; captured wrench is a proxy, originalphysics unchanged'))+'\n')
        return command


class DirectMaterialCarrierGroup:
    """Keep each actual pad's captured preload as its Jacobian changes."""
    def __init__(self, specs, output):
        self.carriers=[DirectMaterialCarrier(spec,output) for spec in specs]
        ids=[int(i) for carrier in self.carriers for i in carrier.ids]
        if len(set(ids))!=len(ids):raise ValueError('Carrier groups must use distinct digits')

    def correct(self,t,O,arm,hand,issued_hand,reference_hand,slider):
        command=reference_hand.copy()
        for carrier in self.carriers:
            command=carrier.correct(t,O,arm,hand,issued_hand,command,slider)
        return command
