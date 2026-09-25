"""Map pinned official MJCF actuators to ArtBot joints for a sensitivity audit.

This deliberately keeps the ArtBot geometry and PhysX engine. It is not a
reproduction of the official MuJoCo model or a hardware calibration.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation
import yaml


def main():
    root = Path(__file__).resolve().parents[1]
    official = root/'runs/wuji-goal/research/wuji-official/wuji-mjlab/src/wuji_mjlab/assets/robots/wuji_hand/mjcf/right_mjlab.xml'
    artbot = root/'assets/hands/wuji_artbot/right.urdf'
    mj = ET.parse(official).getroot()
    ur = ET.parse(artbot).getroot()
    cfg = yaml.safe_load((root/'isaacgymenvs/cfg/hand/wuji.yaml').read_text())
    fingers = dict(thumb=1, index=2, middle=3, ring=4, pinky=5)
    joints = {j.get('name'): j for j in ur.findall('joint')}
    mj_joints = {j.get('name'): j for j in mj.findall('.//worldbody//joint')}
    mj_bodies = {b.find('joint').get('name'): b for b in mj.findall('.//worldbody//body') if b.find('joint') is not None}
    actuators = {a.get('joint'): a for a in mj.findall('actuator/position')}
    rows = []
    for i, name in enumerate(cfg['dof_names']):
        assert name.startswith('hand_r_')
        finger, joint = name[len('hand_r_'):].split('_')
        canonical = 'right_finger%d_%s' % (fingers[finger], joint)
        u, m, a, b = joints[name], mj_joints[canonical], actuators[canonical], mj_bodies[canonical]
        limits = [float(u.find('limit').get(k)) for k in ['lower', 'upper']]
        limit_error = float(np.max(np.abs(np.array(limits)-np.fromstring(m.get('range'), sep=' '))))
        effort_error = abs(float(u.find('limit').get('effort'))-float(a.get('forcerange').split()[1]))
        assert limit_error < 2e-4 and effort_error < 1e-6, (name, limit_error, effort_error)
        assert np.allclose(np.fromstring(u.find('axis').get('xyz'), sep=' '), np.fromstring(m.get('axis'), sep=' '))
        origin = u.find('origin')
        quat = np.fromstring(b.get('quat', '1 0 0 0'), sep=' ')
        rm = Rotation.from_quat(quat[[1, 2, 3, 0]])
        ru = Rotation.from_euler('xyz', np.fromstring(origin.get('rpy'), sep=' '))
        rows.append(dict(artbot=name, official=canonical, limit_error_rad=limit_error,
            effort_error_nm=effort_error,
            origin_position_difference_m=float(np.linalg.norm(np.fromstring(origin.get('xyz'), sep=' ')-np.fromstring(b.get('pos', '0 0 0'), sep=' '))),
            origin_rotation_difference_rad=float((rm.inv()*ru).magnitude()),
            stiffness=float(a.get('kp')), damping=float(a.get('kv')),
            armature=float(m.get('armature', mj.find('default/joint').get('armature'))),
            stiffness_ratio=float(cfg['dof_props']['stiffness'][i])/float(a.get('kp')),
            damping_ratio=float(cfg['dof_props']['damping'][i])/float(a.get('kv'))))
    out = root/'runs/wuji-goal/diagnostics/official-gain-sensitivity'
    out.mkdir(parents=True, exist_ok=True)
    profile = dict(rows=rows, official_sha256=hashlib.sha256(official.read_bytes()).hexdigest(),
        artbot_sha256=hashlib.sha256(artbot.read_bytes()).hexdigest(),
        scope='Matched DOF limit/effort/axis mapping. Geometry and solver remain ArtBot/PhysX. Official gains are a sensitivity setting, not calibrated truth.')
    (out/'mapped-profile.json').write_text(json.dumps(profile, indent=2)+'\n')
    checkpoint = 'runs/wuji_acq_precision_cont_cost1_v1/evaluation/monitor/policies/epoch_000025.pth'
    base = ['--task', 'wuji_acquisition_precision_aug', '--override', 'object=knife_wuji_acquisition_precision',
            '--initial-states', 'runs/wuji-goal/verification/precision-near01-cp125-perturb-small/perturbed_initial_states.npy', '--seed', '1616']
    jobs = []
    for name, props in [('baseline', {}), ('gains10', dict(stiffness=[10.]*20, damping=[.1]*20)),
                        ('official-gains', {k: [r[k] for r in rows] for k in ['stiffness', 'damping']}),
                        ('official-gains-armature', {k: [r[k] for r in rows] for k in ['stiffness', 'damping', 'armature']})]:
        args = list(base)
        for k, values in props.items():
            args += ['--override', 'hand.dof_props.%s=%s' % (k, json.dumps(values, separators=(',', ':')))]
        jobs.append(dict(name='precision-cont-cp25-gain-audit-'+name, checkpoint=checkpoint, args=args))
    queue = root/'runs/wuji-goal/audit-queue-official-gains.json'
    queue.write_text(json.dumps(jobs, indent=2)+'\n')
    print(json.dumps(dict(profile=str(out/'mapped-profile.json'), queue=str(queue),
        kp_ratio_range=[min(r['stiffness_ratio'] for r in rows), max(r['stiffness_ratio'] for r in rows)],
        max_origin_position_difference_m=max(r['origin_position_difference_m'] for r in rows),
        max_origin_rotation_difference_rad=max(r['origin_rotation_difference_rad'] for r in rows))))


if __name__ == '__main__':
    main()
