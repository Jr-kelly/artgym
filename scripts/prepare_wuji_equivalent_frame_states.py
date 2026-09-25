"""Map a successful physical initial state into the generated knife convention.

This is the same grasp and collision geometry, not a new training example or
new grasp success. It separates asset/observation convention from grasp change.
The blade in the acquisition URDF is visual-only and omitted by the generated
asset; physical comparisons use collision boxes, inertia and joint kinematics.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    acquired = root / 'assets/objects/knife_wuji_demo_aligned/000/mobility.urdf'
    generated = root / 'assets/objects/knife_wuji_lowgain_functional20_20260922/000/mobility.urdf'
    source = base / 'near5-cp50-extended-fresh100-seed20261030/seed20261030.npy'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(generated) == '5229c66b183cc6da04190bf2d6cfbd035fadd227340dc8f26602b207171b461c'
    assert sha(source) == '624d1c180f5031ccf25f4ae7212c7048877ab743eaf7ef1490a2eeec2584c1ef'
    a, g = ET.parse(acquired), ET.parse(generated)
    rotation = Rotation.from_euler('x', 90, degrees=True)
    matrix = rotation.as_matrix()
    lower = float(g.find(".//joint[@name='slider']/limit").get('lower'))
    geometry = []
    for name in ['link_0', 'link_1']:
        left = a.find(".//link[@name='%s']" % name)
        right = g.find(".//link[@name='%s']" % name)
        box_a = np.fromstring(left.find('collision/geometry/box').get('size'), sep=' ')
        box_g = np.fromstring(right.find('collision/geometry/box').get('size'), sep=' ')
        assert np.allclose(box_a, np.abs(matrix) @ box_g, rtol=0, atol=1e-12)
        ia = np.diag([float(left.find('inertial/inertia').get(n)) for n in ['ixx', 'iyy', 'izz']])
        ig = np.diag([float(right.find('inertial/inertia').get(n)) for n in ['ixx', 'iyy', 'izz']])
        assert np.allclose(ia, matrix @ ig @ matrix.T, rtol=0, atol=1e-12)
        assert left.find('inertial/mass').get('value') == right.find('inertial/mass').get('value')
        geometry.append(dict(link=name, collision_box_match=True, inertia_match=True, mass_match=True))
    origin_a = np.fromstring(a.find(".//joint[@name='slider']/origin").get('xyz'), sep=' ')
    origin_g = np.fromstring(g.find(".//joint[@name='slider']/origin").get('xyz'), sep=' ')
    axis_a = np.fromstring(a.find(".//joint[@name='slider']/axis").get('xyz'), sep=' ')
    axis_g = np.fromstring(g.find(".//joint[@name='slider']/axis").get('xyz'), sep=' ')
    for travel in np.linspace(0, .05, 51):
        assert np.allclose(origin_a + axis_a * travel,
                           rotation.apply(origin_g + axis_g * (lower + travel)), rtol=0, atol=1e-12)
    states = np.load(source)
    mapped = states.copy()
    for start in [43, 50]:
        mapped[:, start:start + 4] = (Rotation.from_quat(states[:, start:start + 4]) * rotation).as_quat()
    mapped[:, 54] += lower
    assert np.array_equal(mapped[:, :43], states[:, :43])
    assert np.array_equal(mapped[:, 47:50], states[:, 47:50])
    assert np.array_equal(mapped[:, 55:], states[:, 55:])
    # Convert back without changing the quaternion representative's hemisphere.
    recovered = (Rotation.from_quat(mapped[:, 43:47]) * rotation.inv()).as_quat()
    sign = np.where(np.sum(recovered * states[:, 43:47], axis=1, keepdims=True) < 0, -1, 1)
    assert np.allclose(recovered * sign, states[:, 43:47], rtol=0, atol=1e-7)
    out = base / 'equivalent-frame-evaluation-states'
    out.mkdir(exist_ok=False)
    np.save(out / 'initial_states.npy', mapped)
    manifest = dict(status='geometry_and_state_mapping_verified', nominal_grasps=1, trials=100,
                    seed=20261030, same_physical_grasp=True, no_new_grasp_claim=True,
                    geometry_checks=geometry, slider_kinematics_samples=51,
                    mapped_states_sha256=sha(out / 'initial_states.npy'),
                    sources={str(p.relative_to(root)): sha(p) for p in [acquired, generated, source, Path(__file__)]},
                    changes='Object/link quaternions right-multiplied Rx(+90deg); absolute slider offset changed by generated lower bound. All world positions, hand joints, preload and contacts unchanged.',
                    caveat='Actual PhysX reset and learned policy operation still require evaluation. Nominal URDF damping differs but actual object profile overrides both to0.3.')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (base / 'equivalent-frame-transfer-proposal.json').write_text(json.dumps(manifest, indent=2) + '\n')
    jobs = []
    for seconds in [2, 5]:
        jobs.append(dict(name='near5-cp50-equivalent-original-frame-seed30-timed%dseconds' % seconds,
                         module='scripts.audit_wuji_hemisphere_transfer',
                         checkpoint='runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth',
                         args=['--frame-mode', 'acquisition_hemisphere', '--task', 'wuji_acquisition_official_timed2',
                               '--hand', 'wuji_paper_official_actuator', '--object', 'knife_wuji_lowgain_functional20_20260922',
                               '--initial-states', str((out / 'initial_states.npy').relative_to(root)),
                               '--stage-seconds', str(seconds), '--total-seconds', '20', '--seed', '20261030']))
    (base / 'audit-queue-equivalent-frame-transfer.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
