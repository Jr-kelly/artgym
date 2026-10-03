"""Small initial wrist-roll candidate using public estimated contact geometry.

Preserve the planned knife and pad contacts; solve all four active digits and
the entire G2 acquisition path. This is offline IK, not a collision certificate
or pressure controller. No physical asset/contact/slider state is accepted.
"""
import argparse, copy, json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics


def adapt(plan, support, reference, calibration, acquisition, degrees):
    assert 0 < abs(degrees) <= 5
    assert plan['initial_geometry_estimate']['source']
    g = DigitGeometry(); h = g.w; kin = G2Kinematics()
    old = np.asarray(plan['wrist_in_knife'])
    rot = np.eye(4); rot[:3, :3] = Rotation.from_euler('z', degrees, degrees=True).as_matrix()
    new = rot @ old
    normals = np.asarray(plan['contact_normals'])
    digits = ['thumb', 'index', 'middle', 'ring', 'pinky']
    vertices = {f: np.concatenate([v for v, _ in g.meshes['hand_r_'+f+'_pad_link']]) for f in digits}

    def surface(q, finger, wrist):
        frame = wrist @ h.forward(q)['hand_r_'+finger+'_pad_link']
        v = vertices[finger] @ frame[:3, :3].T + frame[:3, 3]
        proj = v @ normals[digits.index(finger)]
        weights = np.exp(-(proj-proj.min())/.0002); weights /= weights.sum()
        return weights @ v, frame[:3, 0]

    def solve(q, finger, seed=None):
        origin, axis = surface(q, finger, old)
        ids = np.array([h.names.index('hand_r_'+finger+'_joint'+str(i)) for i in range(1, 5)])
        seed = q.copy() if seed is None else seed
        def residual(x):
            value = q.copy(); value[ids] = x
            point, direction = surface(value, finger, new)
            return np.r_[(point-origin)*100, (direction-axis)*.12, (x-seed[ids])*.002]
        fit = least_squares(residual, np.clip(seed[ids], h.lower[ids]+1e-5, h.upper[ids]-1e-5),
            bounds=(h.lower[ids]+1e-5, h.upper[ids]-1e-5), max_nfev=180)
        value = q.copy(); value[ids] = fit.x
        return value, float(np.linalg.norm(surface(value, finger, new)[0]-origin))

    touch = np.asarray(plan['touch_q']); chosen = touch.copy(); errors = {}
    for finger in plan['active_fingers']:
        solved, errors[finger] = solve(touch, finger)
        ids = [h.names.index('hand_r_'+finger+'_joint'+str(i)) for i in range(1, 5)]
        chosen[ids] = solved[ids]
    assert max(errors.values()) < .00025, errors
    delta = chosen-touch
    result = copy.deepcopy(plan)
    result.update(wrist_in_knife=new.tolist(), touch_q=chosen.tolist(),
        close_q=np.clip(np.asarray(plan['close_q'])+delta, h.lower+1e-4, h.upper-1e-4).tolist(),
        open_q=np.clip(np.asarray(plan['open_q'])+delta, h.lower+1e-4, h.upper-1e-4).tolist())
    result['close_waypoints'] = [dict(fraction=0., q=result['open_q']),
        dict(fraction=2/3, q=result['touch_q']), dict(fraction=1., q=result['close_q'])]
    result['geometric_pass'] = False
    result['geometric_pass_scope'] = 'New initial wrist pose: contact IK only; no inherited collision certificate. Full native continuous rollout required with original collisions.'
    pressure = copy.deepcopy(support)
    pressure['post_lift_target_q'] = np.clip(np.asarray(support['post_lift_target_q'])+delta,
        h.lower+1e-4, h.upper-1e-4).tolist()
    ref = copy.deepcopy(reference); path_errors = []; seed = chosen.copy()
    for row in ref['rows']:
        q = touch.copy(); q[16:] = row['q_thumb']
        solved, error = solve(q, 'thumb', seed)
        row['q_thumb'] = solved[16:].tolist(); row['point_error_m'] = error
        row['feasible'] = error < .00025
        for key in ['minimum_knife_gap_m', 'minimum_self_gap_m', 'pad_facing_cosine', 'maximum_joint_step_rad', 'message', 'optimizer_success']:
            row.pop(key, None)
        path_errors.append(error); seed = solved
    ref['all_feasible'] = max(path_errors) < .00025
    ref['all_feasible_scope'] = result['geometric_pass_scope']
    assert ref['all_feasible'], max(path_errors)
    move = np.linalg.inv(old) @ new
    path = copy.deepcopy(acquisition); arm_errors = []
    for key in ['approach_q', 'lift_q']:
        original = np.asarray(acquisition[key]); values = []; seed_arm = original[0]
        for q in original:
            target = kin.forward(q) @ move
            solved, error = kin.solve_near(target, seed_arm, max_step=.4)
            assert error['position_m'] < .001 and error['rotation_rad'] < .005, error
            values.append(solved.tolist()); arm_errors.append(error); seed_arm = solved
        path[key] = values
    for key in ['start_wrist_world', 'grasp_wrist_world', 'lift_wrist_world']:
        path[key] = (np.asarray(acquisition[key]) @ move).tolist()
    result['arm_grasp_q'] = path['approach_q'][-1]
    cal = copy.deepcopy(calibration)
    for key in ['object_in_wrist', 'slider_in_wrist']:
        cal[key] = (np.linalg.inv(new) @ old @ np.asarray(calibration[key])).tolist()
    cal['scope'] = 'Original once-initial calibration transformed by known planned wrist pose; no current object/contact input'
    audit = dict(degrees=degrees, initial_estimate=plan['initial_geometry_estimate'],
        contact_IK_errors_m=errors, maximum_path_IK_error_m=max(path_errors),
        new_touch_thumb_rad=chosen[16:].tolist(),
        issued_thumb_upper_margin_rad=(h.upper[16:]-np.asarray(pressure['post_lift_target_q'])[16:]).tolist(),
        maximum_touch_joint_change_rad=float(np.abs(delta).max()), arm_IK=arm_errors,
        scope='Public initial estimate only; original joint bounds and full planned40mm path retained. Motor preload is not force. Original collisions/gravity/effort must be tested in native continuous physics.')
    for value in [result, pressure, ref, path]: value['initial_wrist_roll_candidate'] = dict(degrees=degrees, scope=audit['scope'])
    return result, pressure, ref, cal, path, audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['plan', 'support', 'reference', 'calibration', 'acquisition', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--degrees', type=float, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    values = adapt(*[json.loads(getattr(a, name).read_text()) for name in
        ['plan', 'support', 'reference', 'calibration', 'acquisition']], a.degrees)
    for name, value in zip(['motor-plan.json', 'support.json', 'reference.json', 'calibration.json', 'acquisition.json', 'audit.json'], values):
        (a.output/name).write_text(json.dumps(value, indent=2))
    print(json.dumps(values[-1]), flush=True)


if __name__ == '__main__': main()
