"""Measured joint clearance feedback allowing axial carrier rolling.

Uses collision hull geometry and saved carrier material priors, never native
contact forces. Transverse contact coordinates are preserved to first order;
this is not a collision certificate or an assurance of load retention.
"""
import json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_direct_pickup import smooth


class DirectRollingPairClearance:
    def __init__(self, spec, output):
        self.s = spec
        self.g = DigitGeometry()
        self.k = G2Kinematics()
        self.offset = np.zeros(20)
        self.log = Path(output) / 'direct-rolling-pair-clearance.jsonl'

    def correct(self, t, O, arm, hand, reference_hand):
        q = hand.astype(float)
        L = np.linalg.inv(O) @ self.k.forward(arm)
        pairs = [tuple(pair) for pair in self.s['pairs']]

        def gap(x):
            return min(row['gap_lower_bound_m']
                       for row in self.g.pair_gaps(x, pairs))

        actual_gap = gap(q)
        gradient = np.zeros(20)
        projected = np.zeros(20)
        carriers = []
        for carrier in self.s['carriers']:
            ids = np.asarray(carrier['digit_indices'], dtype=int)
            material = np.asarray(carrier['material_point'])
            name = carrier['material_link']

            def point(x):
                T = L @ self.g.w.forward(x)[name]
                return T[:3, :3] @ material + T[:3, 3]

            P = point(q)
            J = np.empty((3, len(ids)))
            for j, index in enumerate(ids):
                x = q.copy()
                x[index] += 1e-5
                J[:, j] = (point(x) - P) / 1e-5
                gradient[index] = (gap(x) - actual_gap) / 1e-5
            transverse = J[:2]
            tangent = np.eye(len(ids)) - np.linalg.pinv(transverse, rcond=1e-5) @ transverse
            projected[ids] = tangent @ gradient[ids]
            carriers.append((ids, name, P, J))

        error = max(0., self.s['clearance_m'] - actual_gap)
        delta = projected * error / (projected @ projected + 1e-10)
        delta *= self.s.get('gain', .3) * smooth(t / self.s.get('activation_ramp_s', .3))
        delta = np.clip(delta, -self.s.get('max_step_rad', .005),
                        self.s.get('max_step_rad', .005))
        bound = self.s.get('max_correction_rad', .12)
        self.offset = np.clip(self.offset + delta, -bound, bound)
        command = reference_hand.copy()
        ids = np.asarray(sorted({int(i) for c in carriers for i in c[0]}))
        command[ids] = np.clip(command[ids] + self.offset[ids],
                               self.g.w.lower[ids] + .02, self.g.w.upper[ids] - .02)
        self.offset[ids] = command[ids] - reference_hand[ids]
        observations = [dict(material_link=name, actual_material_knife_m=P.tolist(),
                             linear_material_shift_m=(J @ delta[digit_ids]).tolist(),
                             correction_rad=self.offset[digit_ids].tolist())
                        for digit_ids, name, P, J in carriers]
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t), actual_pair_sat_gap_m=actual_gap,
                reference_clearance_m=self.s['clearance_m'], carriers=observations,
                projected_gap_gradient_m_rad=projected.tolist(),
                scope='Measured joints, sim_oracle pose, collision hulls and saved carrier priors. '
                      'XY nullspace permits knife-axis rolling. SAT gap is not penetration depth; '
                      'native contact and load retention require independent checking.')) + '\n')
        return command
