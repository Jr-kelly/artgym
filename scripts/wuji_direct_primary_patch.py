"""Move the acquired opposing grip with live knife geometry through motor IK.

Each distal hull may roll over the real side face. The acquired motor
deformation is retained once, without integrating pressure or changing PD.
Actual native contacts are development evidence, never online control input.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares, linprog
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection, DIGITS


class DirectPrimaryPatch:
    def __init__(self, spec, output):
        self.s = spec
        self.g = DigitGeometry(max_face_axes=10, knife_spec=Path(spec['knife_spec']))
        self.k = G2Kinematics()
        checker = HandIntersection()
        self.self_geometry = checker.g
        self.names = list(spec['materials'])
        self.digits = [n.split('_')[2] for n in self.names]
        self.ids = np.concatenate([np.arange(DIGITS.index(d)*4, DIGITS.index(d)*4+4)
                                   for d in self.digits])
        self.pairs = [p for p in checker.pairs
                      if any(any('_'+d+'_' in n for d in self.digits) for n in p)]
        self.vertices = {n: np.concatenate([v for v, _ in self.g.meshes[n]]) for n in self.names}
        self.initial = None
        self.log = Path(output)/'direct-primary-patch.jsonl'

    def correct(self, t, O, arm, hand, issued, reference, slider):
        q = hand.astype(float)
        L = np.linalg.inv(O)@self.k.forward(arm)
        W = self.k.forward(arm)
        if self.initial is None:
            self.initial = q.copy()
            self.deformation = issued.astype(float)-q
            self.seed = q[self.ids].copy()
        F = self.g.w.forward(q)
        targets, materials, status = {}, {}, {}
        for n in self.names:
            c = self.s['materials'][n]
            T = L@F[n]
            V = self.vertices[n]@T[:3, :3].T+T[:3, 3]
            band, axial = c['side_y_interval_m'], c['axial_interval_m']
            A = np.array([V[:, 1], -V[:, 1], V[:, 2], -V[:, 2]])
            b = np.array([band[1], -band[0], axial[1], -axial[0]])
            sign = float(np.sign(c['side_x_m']))
            fit = linprog(sign*V[:, 0], A_ub=A, b_ub=b,
                          A_eq=np.ones((1, len(V))), b_eq=[1.],
                          bounds=(0, None), method='highs')
            if fit.success:
                materials[n] = fit.x@self.vertices[n]
                targets[n] = fit.x@V
                status[n] = 'rolling side-face hull witness'
            else:
                materials[n] = np.asarray(c['initial_material_point'])
                targets[n] = T[:3, :3]@materials[n]+T[:3, 3]
                targets[n][1] = np.clip(targets[n][1], *band)
                targets[n][2] = np.clip(targets[n][2], *axial)
                status[n] = 'no side-face witness; bounded acquired-material approach'
            targets[n][0] = c['side_x_m']

        def decode(x):
            h = q.copy()
            h[self.ids] = x
            frames = self.g.w.forward(h)
            points = {}
            for n in self.names:
                T = L@frames[n]
                points[n] = T[:3, :3]@materials[n]+T[:3, 3]
            return h, frames, points

        knife_parts = self.g.knife_geometry.collision_parts(slider)
        def residual(x):
            h, frames, points = decode(x)
            r = []
            for n in self.names:
                d = points[n]-targets[n]
                r.extend(d*np.array([700., 250., 40.]))
            r.extend(min(0., a['gap_lower_bound_m']-.00015)*600
                     for a in self.self_geometry.pair_gaps(h, self.pairs, certify_clearance_m=.00015))
            for digit in self.digits:
                for a in self.g.gaps(h, L, slider, digit, frames=frames, knife_parts=knife_parts):
                    bearing = a['knife_link']=='link_0' and (a['hand_link'].endswith('link4') or a['hand_link'].endswith('pad_link'))
                    allow = .0004 if bearing else -.0001
                    r.append(min(0., a['gap_lower_bound_m']+allow)*600)
            for n, parts in self.g.meshes.items():
                if not any('_'+d+'_' in n for d in self.digits):
                    continue
                T = W@frames[n]
                for V, _ in parts:
                    r.append(min(0., float((V@T[:3, :3].T+T[:3, 3])[:, 2].min()-.75005))*600)
            r.extend((x-self.seed)*.012)
            return np.array(r)

        envelope = float(self.s['posture_envelope_rad'])
        lo = np.maximum(self.g.w.lower[self.ids]+.035, self.initial[self.ids]-envelope)
        hi = np.minimum(self.g.w.upper[self.ids]-.035, self.initial[self.ids]+envelope)
        lo = np.maximum(lo, self.seed-.06)
        hi = np.minimum(hi, self.seed+.06)
        fit = least_squares(residual, np.clip(self.seed, lo+1e-7, hi-1e-7),
                            bounds=(lo, hi), max_nfev=12, diff_step=1e-5)
        self.seed = fit.x
        command = reference.copy()
        command[self.ids] = np.clip(self.seed+self.deformation[self.ids],
                                   self.g.w.lower[self.ids]+.001,
                                   self.g.w.upper[self.ids]-.001)
        command[self.ids] = np.clip(command[self.ids], issued[self.ids]-.06, issued[self.ids]+.06)
        if t==0:
            command[self.ids] = issued[self.ids]
        _, _, planned = decode(self.seed)
        _, _, actual = decode(q[self.ids])
        rows = {n:dict(status=status[n], target_knife_m=targets[n].tolist(),
                      planned_point_knife_m=planned[n].tolist(), actual_point_knife_m=actual[n].tolist(),
                      material_point=materials[n].tolist()) for n in self.names}
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t), carriers=rows,
                                   acquired_deformation_rad=self.deformation[self.ids].tolist(),
                                   planned_q=self.seed.tolist(), issued_q=command[self.ids].tolist(),
                                   scope=__doc__))+'\n')
        return command
