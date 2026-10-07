"""Transport this grasp's thumb preload; optionally load its acquired cap facet.

The contact normal is a saved development prior, never a live native-force input.
The wrench is a joint-deflection proxy. Only motor references change.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.record_wuji_flat_table_event import record


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--motor', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--normal-reference', type=float)
    p.add_argument('--lead-time', type=float, default=0.)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    d = json.loads(a.motor.read_text())
    source = Path(d['source'])
    s = np.load(source/'takeover.npz')
    trial, contacts, end = source_contacts(source)
    physics = json.loads((trial/'physics.json').read_text())
    h = WujiKinematics(); k = G2Kinematics()
    servo = d['direct_pressure_path_servo']
    m = np.array(servo['material_point'])
    q = s['robot_q'][7:].astype(float)
    O = transform(s['object_state'][:3], s['object_state'][3:7])
    L = np.linalg.inv(O) @ k.forward(s['robot_q'][:7])
    kp = np.array(physics['kp'][-4:]); kd = np.array(physics['kd'][-4:])

    def jacobian(q, L):
        def point(q):
            T = L @ h.forward(q)['hand_r_thumb_pad_link']
            return T[:3, :3] @ m+T[:3, 3]
        P = point(q); J = np.empty((3, 4))
        for j in range(4):
            qq = q.copy(); qq[16+j] += 1e-5
            J[:, j] = (point(qq)-P)/1e-5
        return J

    J = jacobian(q, L)
    tau = kp*(s['issued_target'][-4:]-q[-4:])
    wrench = np.linalg.solve(J @ J.T+np.eye(3)*1e-7, J @ tau)
    null = tau-J.T @ wrench
    normals = [v['force_normal_contribution_knife_N'] for row in contacts
               for v in row['contacts'] if v['hand_link']=='hand_r_thumb_pad_link'
               and v['knife_link']=='link_1']
    if not normals:
        raise ValueError('Requires actual acquired thumb cap contact')
    normal = np.mean(normals, axis=0); normal /= np.linalg.norm(normal)
    D = d['diagnostics']; original_times = np.array([v['time_s'] for v in D])
    hands = np.array([v['planned_hand_q'] for v in D])
    velocity = np.gradient(hands, original_times, axis=0)
    servo.update(retain_acquired_wrench=True, normal_direction=normal.tolist(),
                 axial_activation_start_s=.5+a.lead_time)
    if a.normal_reference is not None:
        servo['acquired_normal_reference_N'] = a.normal_reference
    new_rows = []; new_diagnostics = []
    if a.lead_time:
        for t in np.arange(0., a.lead_time, .1):
            row = json.loads(json.dumps(d['rows'][0])); row['time_s'] = float(t)
            diag = json.loads(json.dumps(D[0])); diag['time_s'] = float(t)
            new_rows.append(row); new_diagnostics.append(diag)
    for row, diag in zip(d['rows'], D):
        row['time_s'] += a.lead_time; diag['time_s'] += a.lead_time
        new_rows.append(row); new_diagnostics.append(diag)
    velocities = np.r_[np.zeros((len(new_rows)-len(D), 20)), velocity]
    for i, (row, diag) in enumerate(zip(new_rows, new_diagnostics)):
        t = row['time_s']; force = wrench.copy()
        if a.normal_reference is not None:
            force += normal*(a.normal_reference-normal @ wrench)*smooth((t-.1)/1.)
        force[2] += (servo.get('axial_reference_N', .95)-force[2])*smooth(
            (t-servo['axial_activation_start_s'])/1.5)
        qq = np.array(diag['planned_hand_q'])
        LL = np.linalg.inv(np.array(diag['planned_object_world'])) @ k.forward(
            np.array(diag['planned_arm_q']))
        offset = (jacobian(qq, LL).T @ force+null)/kp
        lead = np.clip(kd/kp*velocities[i, -4:], -.07, .07)
        command = np.clip(qq[-4:]+np.clip(offset, -.12, .12)+lead,
                          h.lower[-4:]+.02, h.upper[-4:]-.02)
        if i == 0:
            command = s['issued_target'][-4:].copy()
        row['hand_q'][-4:] = command.tolist()
        row['acquired_thumb_wrench_reference_proxy_N'] = force.tolist()
    d['rows'] = new_rows; d['diagnostics'] = new_diagnostics
    d['acquired_thumb_wrench_transport'] = dict(source=str(source),
        input_motor=str(a.motor), captured_wrench_proxy_N=wrench.tolist(),
        actual_contact_normal_knife=normal.tolist(), normal_reference_N=a.normal_reference,
        lead_time_s=a.lead_time, support_layout='Actual source nonthumb carriers unchanged',
        scope=__doc__)
    assert np.max(abs(np.r_[new_rows[0]['arm_q'], new_rows[0]['hand_q']]-
                      s['issued_target'])) < 1e-6
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(d, indent=2))
    e = record('acquired_facet_thumb_stroke_prepared', [str(a.output)],
               config=d['acquired_thumb_wrench_transport'],
               next_step='Native pressure lead then currentstroke; first physical failure changes next mechanism')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:
        f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
    print(json.dumps(e['config']))


if __name__ == '__main__':
    main()
