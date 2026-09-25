"""Validate a frozen three-grasp teacher on new unfiltered reset perturbations.

The three nominal grasps were trained. Only the perturbations are new. The
unchanged fourth-grasp development cohort stays in every audit as a separate
failure/generalization control. Both 20 s and 60 s protocols are declared here.
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
    model = base / 'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth'
    digest = '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
    frozen = json.loads(model.with_name('manifest.json').read_text())
    assert frozen['status'] == 'frozen' and frozen['sha256'] == digest == sha(model)
    created = datetime.datetime.now(datetime.timezone.utc)
    assert datetime.datetime.fromisoformat(frozen['created']) < created
    source = root / 'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy'
    train = np.load(source)
    assert train.shape == (3, 75)
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    output = base / 'bridge3-fresh200-each-seed20261056'
    output.mkdir(exist_ok=False)
    pieces, splits = [], {}
    for i, label in enumerate(['source', 'novel16', 'novel15']):
        # Separate streams from one new seed, recorded explicitly.
        seed = int(np.random.SeedSequence([20261056, i]).generate_state(1)[0])
        states = states_for_seed(train[i:i+1], seed, hand, trials=200)
        assert states.shape == (200, 75) and np.isfinite(states).all()
        assert len(np.unique(states, axis=0)) == 200
        development = np.load(base / 'bridge3-evaluation-states' / (label + '.npy'))
        assert not set(map(bytes, states)).intersection(map(bytes, development))
        path = output / (label + '.npy')
        np.save(path, states)
        pieces.append(states)
        splits[label] = dict(start=200*i, stop=200*(i+1), seed=seed,
                            nominal_grasps=1, trials=200, fresh_after_freeze=True,
                            sha256=sha(path))
    heldout = base / 'bridge2-evaluation-states/heldout.npy'
    assert np.load(heldout).shape == (32, 75)
    pieces.append(np.load(heldout))
    splits['heldout'] = dict(start=600, stop=632, nominal_grasps=1, trials=32,
                            reused_development=True, sha256=sha(heldout))
    states_path = output / 'mixed632.npy'
    np.save(states_path, np.concatenate(pieces))
    manifest = dict(created_utc=created.isoformat(), scope=__doc__, splits=splits,
                    source_sha256=sha(source), checkpoint_sha256=digest,
                    model_frozen=frozen['created'], no_outcome_filter=True,
                    initial_states_sha256=sha(states_path),
                    perturbation=dict(position_per_axis_m=.0005, joint_rad=.01,
                                      rotation_vector_component_deg=.5),
                    protocols=dict(duration_seconds=[20, 60], command_seconds=[2, 5],
                                   tail_seconds=.3, endpoint_tolerance_m=.002,
                                   maximum_body_drift_m=.01, maximum_body_angle_rad=.25))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    jobs = []
    for duration in [20, 60]:
        for seconds in [2, 5]:
            args = ['--task', 'wuji_acquisition_bridge3_hemisphere', '--hand',
                    'wuji_paper_official_actuator', '--object', 'knife_wuji_bridge3_20260922',
                    '--initial-states', str(states_path.relative_to(root)),
                    '--stage-seconds', str(seconds), '--seed', '20261056']
            if duration == 60:
                args += ['--total-seconds', '60']
            jobs.append(dict(name='bridge3-functionalinit-cp25-fresh632-seed56-%ds-timed%dseconds' % (duration, seconds),
                             module='scripts.audit_wuji_timed_commands' if duration == 20 else 'scripts.audit_wuji_extended_timed_commands',
                             checkpoint=str(model.relative_to(root)), args=args))
    (base / 'audit-queue-bridge3-fresh632-seed56.json').write_text(json.dumps(jobs, indent=2)+'\n')
    (base / 'bridge3-fresh-validation-proposal.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
