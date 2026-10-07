"""Withdraw the acquired ring around the knife before backside loading.

Motor planning only. This keeps the acquired wrist and other digit commands;
native simulation must establish the new support. No physical state writes.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record


def main():
    p = argparse.ArgumentParser()
    for name in ['source', 'endpoint', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--clear-idle-pinky', action='store_true')
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    s = np.load(a.source/'takeover.npz')
    c = json.loads(a.endpoint.read_text())
    g = DigitGeometry(max_face_axes=10, knife_spec=Path(
        'assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    q0 = s['robot_q'][7:].astype(float)
    W = G2Kinematics().forward(s['robot_q'][:7])
    L = np.linalg.inv(transform(s['object_state'][:3], s['object_state'][3:7])) @ W
    name = 'hand_r_ring_pad_link'; ids = np.arange(8 if a.clear_idle_pinky else 12, 16)
    V = np.concatenate([v for v, _ in g.meshes[name]])
    checker = HandIntersection(); source_gaps = g.gaps(q0, L, float(s['slider_q']), 'ring')
    def decode(x):
        h = q0.copy(); h[ids] = x
        T = L @ g.w.forward(h)[name]
        v = V @ T[:3, :3].T + T[:3, 3]
        weights = np.exp((v[:, 1]-v[:, 1].max())/.00015)
        return h, weights @ v / weights.sum()
    _, P0 = decode(q0[ids])
    z = c['target'][2]
    points = [P0, P0+np.array([.005, 0, 0]),
              np.array([.025, -.015, z]), np.array([.003, -.008, z]),
              np.array(c['target'])]
    knots = [0., 1.5, 3.5, 5.5, 7.5]
    seed = q0[ids].copy(); rows = []; diagnostics = []
    record('direct_ring_underpad_waypoint_path_start', [str(a.output)], config={
        'source': str(a.source), 'uncertainty': 'Can ring withdraw +X before going behind -Y without sweeping knife, preserving I/M/thumb?',
        'waypoints_m': [v.tolist() for v in points], 'times_s': knots},
        next_step='All path geometry and continuity before native; first unreachable waypoint requires coordinated wrist')
    for t in np.linspace(0, 8.5, 69):
        j = min(3, max(0, np.searchsorted(knots, t, side='right')-1))
        u = smooth((t-knots[j])/(knots[j+1]-knots[j]))
        target = (1-u)*points[j]+u*points[j+1]
        previous = seed.copy()
        def thresholds(gaps):
            values = []
            for gap, old in zip(gaps, source_gaps):
                free = .0002
                if t <= 1.5:
                    threshold = (1-smooth(t/1.5))*min(free, old['gap_lower_bound_m'])+smooth(t/1.5)*free
                elif t >= 5.5 and gap['hand_link'] == name and gap['knife_link'] == 'link_0':
                    threshold = free + (-.001-free)*smooth((t-5.5)/2.)
                else:
                    threshold = free
                values.append(threshold)
            return values
        def residual(x):
            h, point = decode(x); gaps = g.gaps(h, L, float(s['slider_q']), 'ring')
            r = list((point-target)*350)
            r.extend(min(0, v['gap_lower_bound_m']-limit)*1500
                     for v, limit in zip(gaps, thresholds(gaps)))
            r.extend(min(0, v['gap_lower_bound_m']-.0001)*250
                     for v in g.self_gaps(h, 'ring', certify_clearance_m=.0001))
            if a.clear_idle_pinky:
                r.extend(min(0, v['gap_lower_bound_m']-.0001)*250
                         for v in g.self_gaps(h, 'pinky', certify_clearance_m=.0001))
                r.extend(min(0, v['gap_lower_bound_m']-.0002)*1500
                         for v in g.gaps(h, L, float(s['slider_q']), 'pinky'))
                r.extend((h[8:12]-q0[8:12])*.2)
            r.extend((x-previous)*.015)
            return np.array(r)
        if t > 0:
            lo = np.maximum(g.w.lower[ids]+.06, previous-.14)
            hi = np.minimum(g.w.upper[ids]-.06, previous+.14)
            if a.clear_idle_pinky:
                lo[:4] = np.maximum(lo[:4], q0[8:12]-.3)
                hi[:4] = np.minimum(hi[:4], q0[8:12]+.3)
            fit = least_squares(residual, np.clip(seed, lo+1e-7, hi-1e-7),
                                bounds=(lo, hi), max_nfev=55, diff_step=1e-5)
            seed = fit.x
        h, point = decode(seed); gaps = g.gaps(h, L, float(s['slider_q']), 'ring')
        command = s['issued_target'][7:].astype(float)
        command[ids] = h[ids]+(s['issued_target'][7:][ids]-q0[ids])*(1-smooth(t/1.5))
        rows.append(dict(time_s=float(t), arm_q=s['issued_target'][:7].tolist(), hand_q=command.tolist()))
        d = dict(time_s=float(t), target_m=target.tolist(), point_m=point.tolist(),
                 error_m=float(np.linalg.norm(point-target)), planned_hand_q=h.tolist(),
                 maximum_gap_violation_m=max(max(0, limit-v['gap_lower_bound_m']) for v, limit in zip(gaps, thresholds(gaps))),
                 self=checker.inspect(h), joint_step_rad=float(abs(seed-previous).max()),
                 margin_rad=float(np.minimum(h-g.w.lower, g.w.upper-h).min()))
        diagnostics.append(d); print(json.dumps({k:v for k,v in d.items() if k!='planned_hand_q'}), flush=True)
        if d['error_m'] > .001 or d['maximum_gap_violation_m'] > .0001 or d['self']:
            break
    guard = dict(complete=diagnostics[-1]['time_s'] == 8.5,
                 maximum_error_m=max(d['error_m'] for d in diagnostics),
                 maximum_gap_violation_m=max(d['maximum_gap_violation_m'] for d in diagnostics),
                 self_frames=sum(bool(d['self']) for d in diagnostics),
                 minimum_margin_rad=min(d['margin_rad'] for d in diagnostics))
    out = dict(rows=rows, diagnostics=diagnostics, guard=guard, source=str(a.source), scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(out, indent=2))
    record('direct_ring_underpad_waypoint_path_terminal', [str(a.output/'motor.json')], config=guard,
           next_step='Passing actual ring geometry -> native; blocked fixedwrist waypoint -> coordinate wrist while maintaining other actual carriers')
    print(json.dumps(guard))
    if not guard['complete']: raise SystemExit(2)


if __name__ == '__main__':
    main()
