"""Freeze the two CP50 identities before preparing their paired fresh cohort."""
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    policies = {
        'seed23': ('verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth',
                   '2230146804f9e0de54d4e61ab3efd2d90ec6ef1ee403130cd9a46c235bf860b7'),
        'seed26': ('frozen-candidates/teacher-variable-near5-seed26-cp50/teacher.pth',
                   '0da30325e62a080b32c2db43abbc2b0f38fdd02c0bfce5d815ad0d88966b2716'),
    }
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, (path, expected) in policies.items():
        assert sha(base / path) == expected, name
    output = base / 'cp50-replication-fresh200-seed20261035'
    output.mkdir(exist_ok=False)
    source_path = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
    source = np.load(source_path)
    assert source.shape == (1, 75)
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    reference = base / 'verification/precision-near01-cp125-perturb-small/perturbed_initial_states.npy'
    assert np.array_equal(states_for_seed(source, 1616, hand), np.load(reference))
    states = states_for_seed(source, 20261035, hand, trials=200)
    assert np.isfinite(states).all() and len(np.unique(states, axis=0)) == 200
    np.save(output / 'initial_states.npy', states)
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    seed=20261035, trials=200, nominal_grasps=1,
                    source_sha256=sha(source_path), states_sha256=sha(output / 'initial_states.npy'),
                    policies={name: dict(path=path, sha256=value) for name, (path, value) in policies.items()},
                    reference_recipe_bitwise_equal=True,
                    scope='Both models frozen before a new paired cohort; same nominal grasp perturbations, not unseen grasps. '
                          'The second seed used the same original ancestor checkpoint, not independent training from scratch. '
                          'Long tests reuse seed20261030, separately from fresh200.',
                    joint_criterion='All fixed command tails within 2 mm for 0.3 s; base drift <10 mm and rotation <0.25 rad throughout; alive and finite.',
                    perturbation=dict(position_per_axis_m=.0005, joint_rad=.01, rotation_vector_component_deg=.5))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (base / 'cp50-seed-replication-proposal.json').write_text(json.dumps(manifest, indent=2) + '\n')
    jobs = []
    common = ['--task', 'wuji_acquisition_official_timed2', '--hand', 'wuji_paper_official_actuator',
              '--object', 'knife_wuji_precision_near01']
    for name in ['seed26', 'seed23']:
        for seconds in [2, 5]:
            jobs.append(dict(name='near5-cp50-%s-fresh200-seed20261035-timed%dseconds' % (name, seconds),
                             module='scripts.audit_wuji_timed_commands',
                             checkpoint='runs/wuji-goal/' + policies[name][0],
                             args=common + ['--initial-states', str((output / 'initial_states.npy').relative_to(root)),
                                            '--stage-seconds', str(seconds), '--seed', '20261035']))
    for seconds in [2, 5, 3]:
        jobs.append(dict(name='near5-cp50-seed26-reused100-extended60-timed%dseconds' % seconds,
                         module='scripts.audit_wuji_extended_timed_commands',
                         checkpoint='runs/wuji-goal/' + policies['seed26'][0],
                         args=common + ['--initial-states', 'runs/wuji-goal/near5-cp50-extended-fresh100-seed20261030/seed20261030.npy',
                                        '--total-seconds', '60', '--stage-seconds', str(seconds), '--seed', '20261030']))
    (base / 'audit-queue-cp50-seed-replication.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
