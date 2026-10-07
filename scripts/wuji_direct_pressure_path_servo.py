"""Bounded normal deflection correction on an acquired pad stroke prior.

Inputs are measured joints, issued motor history and explicit object pose.
The force proxy assumes pad-only contact; it is not a force measurement.
Native contact/force logs remain evaluation-only.
"""
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics, transform
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth


class DirectPressurePathServo:
    def __init__(self, motion, output):
        self.s = motion['direct_pressure_path_servo']
        rows = motion['rows']
        self.times = np.array([row['time_s'] for row in rows])
        self.arms = np.array([row['arm_q'] for row in rows])
        self.hands = np.array([row['hand_q'] for row in rows])
        self.k = G2Kinematics()
        self.h = WujiKinematics()
        self.material = np.array(self.s['material_point'])
        self.ids = np.array(self.s.get('digit_indices',[16,17,18,19]),dtype=int)
        self.material_link = self.s.get('material_link','hand_r_thumb_pad_link')
        self.normal_direction = np.array(self.s.get('normal_direction',[0.,-1.,0.]))
        self.kp = np.array(self.s.get('digit_kp',self.s.get('thumb_kp')))
        self.effort = np.array(self.s.get('digit_effort',self.s.get('thumb_effort')))
        self.correction = np.zeros(4)
        self.posture_correction = np.zeros(4)
        self.acquired_wrench = None
        self.log = Path(output) / 'direct-pressure-path-servo.jsonl'
        self.relative_wrist=motion.get('object_relative_wrist_path')
        self.wrist_alignment=None
        self.support_preload=None
        self.reaction_carriers=None
        if 'reaction_material_carriers' in motion:
            from scripts.wuji_direct_material_carrier import DirectMaterialCarrierGroup
            self.reaction_carriers=DirectMaterialCarrierGroup(motion['reaction_material_carriers'],output)
        self.pair_clearance=None
        self.relative_thumb=None
        self.relative_carriers=None
        self.normal_bearings=None
        if 'normal_bearing_transport' in motion:
            from scripts.wuji_direct_normal_bearing_transport import DirectNormalBearingTransport
            self.normal_bearings=DirectNormalBearingTransport(motion['normal_bearing_transport'],output)
        if 'relative_carrier_acquisition_path' in motion:
            from scripts.wuji_direct_relative_carrier_path import DirectRelativeCarrierPath
            self.relative_carriers=DirectRelativeCarrierPath(motion['relative_carrier_acquisition_path'],output)
        if 'relative_thumb_acquisition_path' in motion:
            from scripts.wuji_direct_relative_thumb_path import DirectRelativeThumbPath
            self.relative_thumb=DirectRelativeThumbPath(motion['relative_thumb_acquisition_path'],output)
        if 'rolling_pair_clearance' in self.s:
            from scripts.wuji_direct_rolling_pair_clearance import DirectRollingPairClearance
            self.pair_clearance=DirectRollingPairClearance(self.s['rolling_pair_clearance'],output)
        if 'support_preload_servo' in motion:
            from scripts.wuji_direct_grip_roll_servo import DirectGripRollServo
            self.support_preload=DirectGripRollServo(motion['support_preload_servo'],output)

    def command(self, t, O, arm, hand, issued_arm, issued_hand, slider):
        reference_arm = np.array([np.interp(t, self.times, self.arms[:,j])
                                  for j in range(7)])
        reference_hand = np.array([np.interp(t, self.times, self.hands[:,j])
                                   for j in range(20)])
        return self.correct(t,O,arm,hand,issued_arm,issued_hand,slider,
                            reference_arm,reference_hand)

    def correct(self,t,O,arm,hand,issued_arm,issued_hand,slider,
                reference_arm,reference_hand):
        wrist_tracking=None
        if self.normal_bearings is not None:
            reference_hand=self.normal_bearings.correct(t,O,arm,hand,issued_hand,reference_hand)
        if self.relative_carriers is not None:
            reference_hand=self.relative_carriers.correct(t,O,arm,hand,issued_hand,reference_hand,slider)
        if self.relative_thumb is not None:
            reference_hand=self.relative_thumb.correct(t,O,arm,hand,issued_hand,reference_hand,slider)
        if self.relative_wrist:
            # The development path is certified in knife coordinates. Follow
            # the estimated current knife pose instead of spending its stroke
            # on the observed body drift. This sets motor targets only.
            ref=np.array([np.interp(t,self.times,self.arms[:,j]) for j in range(7)])
            expected=np.array(self.relative_wrist['expected_object_world'])
            goal=O@np.linalg.inv(expected)@self.k.forward(ref)
            if self.wrist_alignment is None:
                self.wrist_alignment=self.k.forward(issued_arm)@np.linalg.inv(goal)
            u=1-smooth(t/self.relative_wrist.get('alignment_decay_s',1.))
            A=transform(self.wrist_alignment[:3,3]*u,Rotation.from_rotvec(Rotation.from_matrix(self.wrist_alignment[:3,:3]).as_rotvec()*u).as_quat())
            reference_arm,wrist_tracking=self.k.solve_near(A@goal,issued_arm.astype(float),max_step=.06,minimum_margin=.06)
        L = np.linalg.inv(O) @ self.k.forward(arm)
        q = hand.astype(float)

        def point(q):
            T = L @ self.h.forward(q)[self.material_link]
            return T[:3,:3] @ self.material + T[:3,3]

        P = point(q)
        J = np.empty((3,4))
        for j in range(4):
            perturbed = q.copy()
            perturbed[self.ids[j]] += 1e-5
            J[:,j] = (point(perturbed)-P)/1e-5
        tau = np.clip(self.kp*(issued_hand[self.ids]-q[self.ids]),
                      -self.effort, self.effort)
        force_proxy = np.linalg.solve(J @ J.T + np.eye(3)*1e-7, J @ tau)
        normal_proxy = float(self.normal_direction @ force_proxy)
        normal_reference = self.s['normal_reference_N']
        desired_force = self.normal_direction * normal_reference
        axial_blend = smooth((t-self.s.get('axial_activation_start_s',.5))/
                             self.s.get('axial_activation_ramp_s',1.5))
        if self.s.get('retain_acquired_wrench'):
            # A new grasp may contact a different cap facet. Preserve its
            # existing transverse preload instead of replacing it with the
            # old grasp's nominal knife-Y force. Only the axial reference
            # changes; the captured wrench remains a deflection proxy.
            if self.acquired_wrench is None:
                self.acquired_wrench = force_proxy.copy()
            desired_force = self.acquired_wrench.copy()
            if self.s.get('acquired_normal_reference_N') is not None:
                normal_blend = smooth((t-self.s.get('normal_activation_start_s',.1))/
                                      self.s.get('normal_activation_ramp_s',1.))
                desired_force += self.normal_direction*(
                    self.s['acquired_normal_reference_N']-
                    float(self.normal_direction @ self.acquired_wrench))*normal_blend
            normal_reference = float(self.normal_direction @ desired_force)
            desired_force[2] += (self.s.get('axial_reference_N',0.)-
                                desired_force[2])*axial_blend
        else:
            desired_force[2] += self.s.get('axial_reference_N',0.)*axial_blend
        if self.s.get('force_reference_path'):
            path = self.s['force_reference_path']
            times = np.array([row['time_s'] for row in path])
            forces = np.array([row['wrench_proxy_N'] for row in path])
            desired_force = np.array([np.interp(t, times, forces[:, j])
                                      for j in range(3)])
            if self.acquired_wrench is None:
                self.acquired_wrench = force_proxy.copy()
            desired_force += (self.acquired_wrench-forces[0])*(1-smooth(t/1.))
            normal_reference = float(self.normal_direction @ desired_force)
        error = normal_reference - normal_proxy
        if self.s.get('full_wrench_tracking'):
            delta = J.T @ (desired_force-force_proxy) / self.kp * self.s['gain']
        else:
            delta = J.T @ self.normal_direction / self.kp * error * self.s['gain']
        delta *= smooth((t-self.s.get('activation_start_s',.1))/
                        self.s.get('activation_ramp_s',.4))
        delta = np.clip(delta, -self.s['max_step_rad'], self.s['max_step_rad'])
        self.correction = np.clip(self.correction+delta,
                                  -self.s['max_correction_rad'],
                                  self.s['max_correction_rad'])
        reserve = self.s.get('material_nullspace_reserve_rad')
        if reserve is not None:
            # Redistribute a loaded thumb posture without moving its contact
            # point to first order. This is measured-joint feedback, rather
            # than another fixed force or target bias.
            tangent = np.eye(4)-np.linalg.pinv(J, rcond=1e-5) @ J
            error = (np.maximum(self.h.lower[self.ids]+reserve-q[self.ids], 0.)-
                     np.maximum(q[self.ids]-self.h.upper[self.ids]+reserve, 0.))
            posture_delta = tangent @ error*self.s['gain']
            posture_delta*=smooth((t-self.s.get('posture_activation_start_s',0.))/
                                  self.s.get('posture_activation_ramp_s',.3))
            posture_delta = np.clip(posture_delta, -self.s['max_step_rad'],
                                    self.s['max_step_rad'])
            bound = self.s.get('max_posture_correction_rad', .12)
            self.posture_correction = np.clip(self.posture_correction+posture_delta,
                                              -bound, bound)
        command = reference_hand.copy()
        motor_margin=self.s.get('motor_margin_rad',.02)
        upper = self.h.upper[self.ids].copy()-motor_margin
        if self.ids[0] == 16:
            upper[0] = min(upper[0],self.s.get('thumb1_target_upper_rad',upper[0]))
        command[self.ids] = np.clip(reference_hand[self.ids]+self.correction+
                                    self.posture_correction,
                                    self.h.lower[self.ids]+motor_margin, upper)
        # Avoid integration beyond a clamped target; preserve original limits.
        self.correction = (command[self.ids] - reference_hand[self.ids]-
                           self.posture_correction)
        if self.support_preload is not None:
            command=self.support_preload.correct(t,O,arm,hand,issued_hand,command)
        if self.reaction_carriers is not None:
            command=self.reaction_carriers.correct(t,O,arm,hand,issued_hand,command,slider)
        if self.pair_clearance is not None:
            command=self.pair_clearance.correct(t,O,arm,hand,command)
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t),
                pose_source='sim_oracle explicit pose, measured joints and motor history',
                material_point_knife_m=P.tolist(), slider_m=float(slider),
                normal_joint_deflection_proxy_N=normal_proxy,
                joint_deflection_wrench_proxy_N=force_proxy.tolist(),
                desired_wrench_reference_N=desired_force.tolist(),
                normal_reference_N=normal_reference,
                acquired_wrench_proxy_N=(None if self.acquired_wrench is None
                                        else self.acquired_wrench.tolist()),
                correction_rad=self.correction.tolist(),
                material_nullspace_posture_correction_rad=self.posture_correction.tolist(),
                material_link=self.material_link,
                object_relative_wrist_ik=wrist_tracking,
                issued_digit_q=command[self.ids].tolist(),
                issued_thumb_q=command[16:].tolist(),
                scope='No nativecontact/force input; proxy assumes pad-only contact. '
                      'Original finite PD, effort, gravity and joint limits unchanged'))+'\n')
        return reference_arm, command
