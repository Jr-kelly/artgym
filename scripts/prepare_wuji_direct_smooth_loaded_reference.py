"""Transport acquired PD preload on a planned path, without live IK differencing.

This is a motor reference: the captured wrench is a deflection proxy and never
a measurement. Native physics and all drive settings remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.record_wuji_flat_table_event import record


def main():
    p = argparse.ArgumentParser()
    for name in ['motor', 'source', 'carriers', 'physics', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    motion = json.loads(a.motor.read_text())
    specs = json.loads(a.carriers.read_text())
    source = np.load(a.source/'takeover.npz')
    physics = json.loads(a.physics.read_text())
    g = DigitGeometry(max_face_axes=10, knife_spec=Path(specs[0]['knife_spec']))
    k = G2Kinematics()
    O = transform(source['object_state'][:3], source['object_state'][3:7])
    initial = source['robot_q'][7:].astype(float)
    L0 = np.linalg.inv(O) @ k.forward(source['robot_q'][:7])
    times = np.array([v['time_s'] for v in motion['rows']])
    planned = np.array([v['planned_hand_q'] for v in motion['diagnostics']])
    velocity = np.gradient(planned, times, axis=0)
    captured = []
    for spec in specs:
        ids = np.array(spec['digit_indices'])
        name = spec['material_link']
        material = np.array(spec['material_point'])
        kp = np.array(physics['kp'])[7:][ids]
        kd = np.array(physics['kd'])[7:][ids]

        def jacobian(q, L, foot=None):
            point_material=material if foot is None else foot
            def point(h):
                T = L @ g.w.forward(h)[name]
                return T[:3, :3] @ point_material + T[:3, 3]
            P = point(q)
            J = np.empty((3, len(ids)))
            for j, index in enumerate(ids):
                h = q.copy(); h[index] += 1e-5
                J[:, j] = (point(h)-P)/1e-5
            return J

        J0 = jacobian(initial, L0)
        tau = kp*(source['issued_target'][7:][ids]-initial[ids])
        force = np.linalg.solve(J0 @ J0.T + np.eye(3)*1e-7, J0 @ tau)
        null = tau-J0.T @ force
        preloads = []
        for i, (row, d) in enumerate(zip(motion['rows'], motion['diagnostics'])):
            L = np.linalg.inv(np.array(d['expected_object_world'])) @ k.forward(
                np.array(d['planned_arm_q']))
            foot=np.array(d.get('planned_support_materials',{}).get(name,material))
            offset = (jacobian(planned[i], L,foot).T @ force+null)/kp
            # Keep the existing carrier family's bounds, with exact initial command.
            # An opt-in bound can retain an already acquired larger preload;
            # it never changes the drive or captured wrench reference.
            bound = float(spec.get('max_preload_rad', .1))
            offset = np.clip(offset, -bound, bound)
            lead = np.clip(kd/kp*velocity[i, ids], -.07, .07)
            command = planned[i, ids]+offset+lead
            command = np.clip(command, g.w.lower[ids]+.02, g.w.upper[ids]-.02)
            if i == 0:
                command = source['issued_target'][7:][ids].copy()
            hand = np.array(row['hand_q']); hand[ids] = command
            row['hand_q'] = hand.tolist()
            row.setdefault('planned_loaded_reference', {})[name] = dict(
                preload_rad=offset.tolist(), original_damping_lead_rad=lead.tolist())
            preloads.append(offset)
        captured.append(dict(material_link=name, captured_proxy_N=force.tolist(),
            null_tau_Nm=null.tolist(), maximum_preload_rad=float(abs(np.array(preloads)).max())))
    motion.pop('direct_material_carriers', None)
    motion.pop('direct_material_carrier', None)
    motion['development_abort_on_translation_m'] = .025
    motion['smooth_loaded_reference'] = dict(source=str(a.source),
        input_motor=str(a.motor), input_sha256=hashlib.sha256(a.motor.read_bytes()).hexdigest(),
        captured=captured, scope=__doc__, live_reference_differentiation=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(motion, indent=2))
    record('direct_smooth_loaded_reference_prepared', [str(a.output)],
        config=motion['smooth_loaded_reference'], next_step=
        'One native approach distinguishes noisy live reference from smooth planned preload transport; failure requires support/path structural change, no gain scan')
    print(json.dumps(motion['smooth_loaded_reference']))


if __name__ == '__main__':
    main()
