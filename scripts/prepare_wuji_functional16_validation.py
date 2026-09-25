"""Freeze a fresh perturbation test of functional20 training row16 after CP50.

This is one learned additional training grasp, not an unseen grasp. The original
CP50 and adapted CP50 are evaluated on the same new cohort. Source retention is
tested separately on existing source states. No state is filtered by outcome.
"""
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    checkpoints = {
        'adapted': ('frozen-candidates/teacher-functional20-hemisphere-seed34-cp50/teacher.pth',
                    'bb247e2d0a704fccb3623c1e37b0728079c2b0f955547e0e187d2560ac0ace31'),
        'original': ('verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth',
                     '2230146804f9e0de54d4e61ab3efd2d90ec6ef1ee403130cd9a46c235bf860b7'),
    }
    for path, digest in checkpoints.values():
        assert sha(base / path) == digest
    source = root / 'caches/initial_grasp/wuji/knife_wuji_lowgain_functional20_20260922/000/train/valid_grasps.npy'
    nominal = np.load(source)[16:17]
    assert np.array_equal(nominal, np.load(root / 'caches/initial_grasp/wuji/knife_wuji_bridge2_20260922/000/train/valid_grasps.npy')[1:2])
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    states = states_for_seed(nominal, 20261038, hand, trials=200)
    assert states.shape == (200, 75) and np.isfinite(states).all()
    assert len(np.unique(states, axis=0)) == 200
    out = base / 'functional16-fresh200-seed20261038'
    out.mkdir(exist_ok=False)
    np.save(out / 'initial_states.npy', states)
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope=__doc__,
                    seed=20261038, nominal_grasps=1, trials=200, training_row=16,
                    source_sha256=sha(source), states_sha256=sha(out / 'initial_states.npy'),
                    checkpoints={key: dict(path=path, sha256=digest) for key, (path, digest) in checkpoints.items()},
                    same_physics_and_inputs=True, filtered=False,
                    perturbation=dict(position_per_axis_m=.0005, joint_rad=.01, rotation_vector_component_deg=.5))
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (base / 'functional16-validation-proposal.json').write_text(json.dumps(manifest, indent=2) + '\n')
    common = ['--task', 'wuji_acquisition_functional_hemisphere', '--hand', 'wuji_paper_official_actuator',
              '--object', 'knife_wuji_lowgain_functional20_20260922']
    jobs = []
    for identity in ['adapted', 'original']:
        for seconds in [2, 5]:
            jobs.append(dict(name='functional16-%s-cp50-fresh200-seed38-timed%dseconds' % (identity, seconds),
                             module='scripts.audit_wuji_timed_commands', checkpoint='runs/wuji-goal/' + checkpoints[identity][0],
                             args=common + ['--initial-states', str((out / 'initial_states.npy').relative_to(root)),
                                            '--stage-seconds', str(seconds), '--seed', '20261038']))
    for seconds in [2, 5]:
        jobs.append(dict(name='functional20-adapted-cp50-source-retention100-timed%dseconds' % seconds,
                         module='scripts.audit_wuji_timed_commands', checkpoint='runs/wuji-goal/' + checkpoints['adapted'][0],
                         args=common + ['--initial-states', 'runs/wuji-goal/bridge2-evaluation-states/source.npy',
                                        '--stage-seconds', str(seconds), '--seed', '20261036']))
    (base / 'audit-queue-functional16-validation.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
