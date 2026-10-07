"""Retain acquired grip preload through a roll using bounded joint feedback.

Material points identify prior actual carriers; their positions are not locked.
The deflection projection is a load proxy, never a measured contact force.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics, ROOT
from scripts.wuji_direct_pickup import smooth


class DirectGripRollServo:
    def __init__(self, spec, output):
        self.s = spec
        self.k = G2Kinematics()
        self.h = WujiKinematics()
        joints = {j.get('name'): j for j in ET.parse(ROOT / self.h.config['asset']).getroot().findall('joint')}
        self.effort = np.array([float(joints[n].find('limit').get('effort')) for n in self.h.names])
        self.offset = np.zeros(20)
        self.references = None
        self.wrench_references = []
        self.held_commands = {}
        self.log = Path(output) / 'direct-grip-roll-servo.jsonl'

    def correct(self, t, O, arm, hand, issued_hand, reference_hand):
        L = np.linalg.inv(O) @ self.k.forward(arm)
        q = hand.astype(float)
        observations = []
        if self.references is None:
            self.references = []
        capture = not self.references
        for number, carrier in enumerate(self.s['carriers']):
            ids = np.array(carrier['digit_indices'], dtype=int)
            kp = np.array(carrier['digit_kp'])
            m = np.array(carrier['material_point'])
            if carrier.get('material_point_path'):
                path=carrier['material_point_path']
                times=np.array([row['time_s'] for row in path])
                points=np.array([row['material_point'] for row in path])
                m=np.array([np.interp(t,times,points[:,j]) for j in range(3)])
            name = carrier['material_link']
            direction = np.array([1., 0., 0.]) if '_thumb_' in name else np.array([-1., 0., 0.])
            if 'normal_direction_knife' in carrier:
                direction=np.array(carrier['normal_direction_knife'],dtype=float)
                direction/=np.linalg.norm(direction)

            def point(x):
                T = L @ self.h.forward(x)[name]
                return T[:3, :3] @ m + T[:3, 3]

            P = point(q)
            J = np.empty((3, 4))
            for j, index in enumerate(ids):
                x = q.copy()
                x[index] += 1e-5
                J[:, j] = (point(x) - P) / 1e-5
            tau = np.clip(kp * (issued_hand[ids] - q[ids]),
                          -self.effort[ids], self.effort[ids])
            proxy = np.linalg.solve(J @ J.T + np.eye(3)*1e-7, J @ tau)
            normal = float(direction @ proxy)
            if capture:
                self.references.append(normal)
                self.wrench_references.append(proxy.copy())
            desired = carrier.get('normal_reference_N',self.references[number])
            force_error=direction*(desired-normal)
            desired_wrench = None
            if carrier.get('retain_acquired_wrench'):
                # During a push the carriers must provide an axial reaction,
                # not merely retain a side normal. Start at the actually
                # acquired deflection proxy and ramp the opposing increment
                # together with the thumb; no native forces enter this loop.
                desired_wrench = self.wrench_references[number].copy()
                blend = smooth((t-carrier.get('axial_activation_start_s', 2.))/
                               carrier.get('axial_activation_ramp_s', 1.5))
                desired_wrench[2] += carrier.get('axial_reaction_increment_N', 0.) * blend
                force_error = desired_wrench - proxy
            up_reference=carrier.get('world_up_reference_N')
            if up_reference is not None:
                # Supply the known object weight through frictional support,
                # retaining the captured normal load. This is a deflection
                # proxy in the same original bounded motor loop.
                up=O[:3,:3].T@np.array([0.,0.,float(up_reference)])
                tangent=np.eye(3)-np.outer(direction,direction)
                force_error+=tangent@(up-proxy)
            delta = J.T @ force_error / kp * self.s['gain']
            delta *= smooth(t / self.s['activation_ramp_s'])
            posture_delta = np.zeros(4)
            reserve = carrier.get('loaded_joint_reserve_rad')
            material_reserve = carrier.get('material_nullspace_reserve_rad')
            if reserve is not None:
                # Shift posture in the contact-normal tangent subspace. This
                # redistributes joint loading without increasing captured
                # normal reference or locking a material point to the knife.
                normal_jacobian = direction @ J
                tangent = np.eye(4)-np.outer(normal_jacobian, normal_jacobian)/(
                    normal_jacobian @ normal_jacobian+1e-12)
                error = np.maximum(self.h.lower[ids]+reserve-q[ids], 0.)
                posture_delta = tangent @ error*self.s['gain']
                posture_delta *= smooth(t/self.s['activation_ramp_s'])
                delta += posture_delta
            if material_reserve is not None:
                # The previous normal-only projection allowed tangential
                # carrier motion. This opt-in uses the full material-point
                # Jacobian, preserving all three first-order coordinates.
                tangent=np.eye(4)-np.linalg.pinv(J,rcond=1e-5)@J
                error=np.maximum(self.h.lower[ids]+material_reserve-q[ids],0.)
                posture_delta=tangent@error*self.s['gain']*smooth(t/self.s['activation_ramp_s'])
                delta+=posture_delta
            delta = np.clip(delta, -self.s['max_step_rad'], self.s['max_step_rad'])
            for index in carrier.get('hold_acquired_joint_indices',[]):
                if index not in ids:
                    raise ValueError('Held joint must belong to this carrier')
                if index not in self.held_commands:
                    self.held_commands[index]=float(issued_hand[index])
                delta[np.flatnonzero(ids==index)[0]]=0.
            self.offset[ids] = np.clip(self.offset[ids]+delta,
                                       -self.s['max_correction_rad'], self.s['max_correction_rad'])
            observations.append(dict(material_link=name, point_knife_m=P.tolist(),
                inward_deflection_proxy_N=normal, captured_reference_proxy_N=desired,
                original_captured_proxy_N=self.references[number],
                captured_wrench_proxy_N=self.wrench_references[number].tolist(),
                desired_wrench_proxy_N=(None if desired_wrench is None else desired_wrench.tolist()),
                actual_wrench_proxy_N=proxy.tolist(),
                normal_direction_knife=direction.tolist(),
                world_up_reference_proxy_N=up_reference,
                loaded_joint_reserve_rad=reserve,
                material_nullspace_reserve_rad=material_reserve,
                material_linear_posture_displacement_m=(J@posture_delta).tolist(),
                normal_tangent_posture_delta_rad=posture_delta.tolist(),
                offset_rad=self.offset[ids].tolist()))
        upper=self.h.upper.copy()
        for key,margin in self.s.get('command_upper_margin_rad',{}).items():
            index=int(key)
            if not (0<=index<20 and 0<float(margin)<upper[index]-self.h.lower[index]):
                raise ValueError('Invalid motor command reserve')
            upper[index]-=float(margin)
        command = np.clip(reference_hand+self.offset, self.h.lower, upper)
        for index,value in self.held_commands.items():
            if value>upper[index]:raise ValueError('Acquired held command conflicts with requested reserve')
            command[index]=value
        self.offset = command-reference_hand
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t), carriers=observations,
                scope='Live sim_oracle pose, measured joints and issued motor history; '
                      'no native contact/force input, spatial material lock or physics state writes. '
                      'Original PD/effort/limits preserved; proxy is not measured force.'))+'\n')
        return command
