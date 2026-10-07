"""Acquire a center-side ring contact using live pose, retaining old carriers."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_direct_pickup import smooth


class DirectLiveRing:
    def __init__(self, spec, output):
        self.s = spec
        self.k = G2Kinematics()
        self.g = DigitGeometry(max_face_axes=10, knife_spec=Path(spec['knife_spec']))
        self.arm = None
        self.initial = None
        self.seed = np.array(spec['endpoint_ring_q'])
        self.name = 'hand_r_ring_pad_link'
        self.V = np.concatenate([v for v, _ in self.g.meshes[self.name]])
        self.inward = np.array(spec.get('support_inward_normal_knife', [-1., 0., 0.]), dtype=float)
        self.inward /= np.linalg.norm(self.inward)
        self.log = Path(output) / 'direct-live-ring.jsonl'

    def command(self, t, O, arm, hand, issued_arm, issued_hand, slider):
        if self.arm is None:
            self.arm = issued_arm.copy()
            self.initial = issued_hand.copy()
            self.initial_wrist = self.k.forward(issued_arm)
        lift_ik=None
        if self.s.get('initial_world_lift_m'):
            goal=self.initial_wrist.copy()
            goal[2,3]+=float(self.s['initial_world_lift_m'])*smooth(t/self.s.get('initial_world_lift_duration_s',1.2))
            self.arm,lift_ik=self.k.solve_near(goal,self.arm.astype(float),max_step=.1,minimum_margin=.05)
        delay=float(self.s.get('acquisition_delay_s',0.))
        if t<delay:
            with self.log.open('a') as f:
                f.write(json.dumps(dict(time_s=float(t),initial_lift_active=True,ring_acquisition_delayed=True,lift_ik=lift_ik,scope='Actual acquired wrist motor-only lift, other issued carriers held, ring optimizer deferred until table space exists.'))+'\n')
            return self.arm.copy(),self.initial.copy()
        W = self.k.forward(arm)
        L = np.linalg.inv(O) @ W
        q = hand.astype(float)
        target = np.array(self.s['target_knife_m'])

        def decode(x):
            h = q.copy()
            h[12:16] = x
            F = self.g.w.forward(h)
            T = L @ F[self.name]
            v = self.V @ T[:3, :3].T + T[:3, 3]
            depth = v @ self.inward
            weights = np.exp((depth-depth.max())/.00025)
            return h, F, weights @ v / weights.sum()

        def residual(x):
            h, F, P = decode(x)
            r = list((P-target)*300)
            r.extend(((L @ F[self.name])[:3, 0]-self.inward)*self.s.get('normal_weight', .3))
            for a in self.g.gaps(h, L, slider, 'ring'):
                allow = self.s.get('support_preload_m', .0008) if a['knife_link']=='link_0' and a['hand_link'] in [self.name, 'hand_r_ring_link4'] else -.0001
                r.append(min(0., a['gap_lower_bound_m']+allow)*400)
            r.extend(min(0., a['gap_lower_bound_m']-.0002)*200
                     for a in self.g.self_gaps(h, 'ring', certify_clearance_m=.0002))
            for n, parts in self.g.meshes.items():
                if '_ring_' not in n:
                    continue
                T = W @ F[n]
                r.extend(min(0., float((v@T[:3, :3].T+T[:3, 3])[:, 2].min()-.7505))*400 for v, _ in parts)
            r.extend((x-self.seed)*.005)
            return np.array(r)

        lo = self.g.w.lower[12:16]+.04
        hi = self.g.w.upper[12:16]-.04
        fit = least_squares(residual, np.clip(self.seed, lo+1e-6, hi-1e-6),
                            bounds=(lo, hi), max_nfev=20, diff_step=1e-5)
        self.seed = fit.x
        u = smooth((t-delay)/self.s['acquisition_s'])
        command = self.initial.copy()
        command[12:16] = (1-u)*self.initial[12:16]+u*self.seed
        # Motor slew only; the physical velocity, torque and collision limits remain unchanged.
        command[12:16] = np.clip(command[12:16], issued_hand[12:16]-.10, issued_hand[12:16]+.10)
        _, _, P = decode(self.seed)
        with self.log.open('a') as f:
            f.write(json.dumps(dict(time_s=float(t), target_knife_m=target.tolist(),
                planned_point_knife_m=P.tolist(), endpoint_error_m=float(np.linalg.norm(P-target)),
                support_inward_normal_knife=self.inward.tolist(),
                issued_ring_q=command[12:16].tolist(),
                initial_world_lift_m=self.s.get('initial_world_lift_m',0.),
                lift_ik=lift_ik,
                scope='Live sim_oracle object pose and measured FK; ring-only motor update. '
                      'Other carrier motor history retained; no native contact input or physical state writes.'))+'\n')
        return self.arm.copy(), command
