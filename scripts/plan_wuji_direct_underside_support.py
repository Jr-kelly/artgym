"""Joint wrist/fingers to acquire tail underside while retaining actual tripod."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.record_wuji_flat_table_event import record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    s = np.load(a.source/'takeover.npz')
    g = DigitGeometry(max_face_axes=10, knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k = G2Kinematics()
    O = transform(s['object_state'][:3], s['object_state'][3:7])
    L = np.linalg.inv(O) @ k.forward(s['robot_q'][:7])
    q = s['robot_q'][7:].astype(float)
    F0 = g.w.forward(q)
    _, native, end = source_contacts(a.source)
    names = ['hand_r_index_link4', 'hand_r_ring_pad_link', 'hand_r_thumb_link4']
    materials, points = {}, {}
    for name in names:
        C = [c for r in native if r['time_s'] > end-.1 for c in r['contacts'] if c['hand_link']==name]
        weights = np.array([c['normal_magnitude_N'] for c in C])
        assert len(C) and weights.sum()>0
        materials[name] = np.average([c['position_hand_link_m'] for c in C], axis=0, weights=weights)
        T = L @ F0[name]
        points[name] = T[:3, :3] @ materials[name] + T[:3, 3]
    name = 'hand_r_middle_pad_link'
    V = np.concatenate([v for v, _ in g.meshes[name]])
    ids = np.r_[0:8, 12:20]
    x0 = np.r_[L[:3, 3], Rotation.from_matrix(L[:3, :3]).as_rotvec(), q[ids], 0., -.059]
    lo = np.r_[x0[:3]-.055, x0[3:6]-.9, g.w.lower[ids]+.025, -.006, -.067]
    hi = np.r_[x0[:3]+.055, x0[3:6]+.9, g.w.upper[ids]-.025, .006, -.053]

    def decode(x):
        l = transform(x[:3], Rotation.from_rotvec(x[3:6]).as_quat())
        h = q.copy()
        h[ids] = x[6:-2]
        F = g.w.forward(h)
        T = l @ F[name]
        v = V @ T[:3, :3].T + T[:3, 3]
        weights = np.exp(-(v[:, 1]-v[:, 1].min())/.0002)
        m = weights @ V / weights.sum()
        P = T[:3, :3] @ m + T[:3, 3]
        return l, h, F, P, m

    def residual(x):
        l, h, F, P, _ = decode(x)
        r = []
        for n, m in materials.items():
            T = l @ F[n]
            r.extend((T[:3, :3] @ m+T[:3, 3]-points[n])*500)
        r.extend((P-[x[-2], .0035, x[-1]])*300)
        r.extend(((l @ F[name])[:3, 0]-[0., -1., 0.])*.2)
        for finger in ['index', 'middle', 'ring', 'thumb']:
            for gap in g.gaps(h, l, s['slider_q'], finger):
                threshold = -.0006 if gap['hand_link']==name and gap['knife_link']=='link_0' else -.00008 if gap['hand_link'] in materials and gap['knife_link']=='link_0' else .0001
                r.append(min(0., gap['gap_lower_bound_m']-threshold)*600)
            r.extend(min(0., v['gap_lower_bound_m']-.0002)*200 for v in g.self_gaps(h, finger, certify_clearance_m=.0002))
        W = O @ l
        for n, parts in g.meshes.items():
            T = W @ F[n]
            r.extend(min(0., float((v @ T[:3, :3].T+T[:3, 3])[:, 2].min()-.7505))*400 for v, _ in parts)
        r.extend((x-x0)*.012)
        return np.array(r)

    record('direct_joint_underside_geometry_start', [str(a.output)], config={
        'uncertainty': 'Fixedwrist middle misses19mm; can wrist+16fingerDOF retain actualtripod while truepad acquires+Y tail behindslider?',
        'decision': 'Submm support/middle and wholegeometry -> contactgait/native; blocked -> new initialfunctional grip topology'},
        next_step='Inspect actual-carrier endpoint, arm reach and all affected geometry')
    fit = least_squares(residual, np.clip(x0, lo+1e-6, hi-1e-6), bounds=(lo, hi), max_nfev=150, diff_step=1e-5)
    l, h, F, P, m = decode(fit.x)
    arm, e = k.solve_near(O @ l, s['robot_q'][:7].astype(float), max_step=1., minimum_margin=.06)
    errors = {n: float(np.linalg.norm((l @ F[n])[:3, :3] @ material+(l @ F[n])[:3, 3]-points[n])) for n, material in materials.items()}
    d = dict(source=str(a.source), wrist_in_knife=l.tolist(), hand_q=h.tolist(), arm_q=arm.tolist(), arm_ik=e,
        support_materials={n: m.tolist() for n, m in materials.items()}, support_points={n: p.tolist() for n, p in points.items()},
        support_errors_m=errors, middle_point=P.tolist(), middle_target=[float(fit.x[-2]), .0035, float(fit.x[-1])],
        middle_material=m.tolist(), middle_error_m=float(np.linalg.norm(P-[fit.x[-2], .0035, fit.x[-1]])),
        middle_normal=(l @ F[name])[:3, 0].tolist(), self_intersections=HandIntersection().inspect(h),
        scope='Actual measured tripod material constraints, planned only; no simulator state writes or force measurement.')
    (a.output/'candidate.json').write_text(json.dumps(d, indent=2))
    brief = {key: value for key, value in d.items() if key not in ['hand_q', 'arm_q', 'wrist_in_knife', 'support_materials', 'support_points']}
    print(json.dumps(brief))
    record('direct_joint_underside_geometry_terminal', [str(a.output/'candidate.json')], config=brief,
        next_step='Only feasibleendpoint creates supportedcontactgait; failedconstraints guide topology change')


if __name__=='__main__':
    main()
