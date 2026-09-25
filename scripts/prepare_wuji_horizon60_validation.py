"""Fresh long-rollout perturbations for the frozen horizon60 CP100 candidate."""
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    checkpoint = base / 'frozen-candidates/teacher-horizon60-seed33-cp100/teacher.pth'
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert digest == '12e41367735fae38cab3e71af9f56c02efb678a6bc92a62f2b3d8f8a9944c37c'
    source = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    states = states_for_seed(np.load(source), 20261039, hand)
    assert states.shape == (100, 75) and np.isfinite(states).all()
    out = base / 'horizon60-cp100-fresh100-seed20261039'
    out.mkdir(exist_ok=False)
    np.save(out / 'initial_states.npy', states)
    metadata = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    checkpoint=str(checkpoint.relative_to(root)), checkpoint_sha256=digest,
                    seed=20261039, nominal_grasps=1, trials=100,
                    states_sha256=hashlib.sha256((out / 'initial_states.npy').read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    scope='Model frozen before this new100cohort. Same nominal source grasp, no filtering. '
                          'All2/5/3sprotocols share these100states; 60srollout each. Notunseen-grasp or hardware.',
                    perturbation=dict(position_per_axis_m=.0005, joint_rad=.01, rotation_vector_component_deg=.5))
    (out / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (base / 'horizon60-cp100-fresh-validation-proposal.json').write_text(json.dumps(metadata, indent=2) + '\n')
    jobs = []
    for seconds in [2, 5, 3]:
        jobs.append(dict(name='horizon60-cp100-fresh100-seed39-extended60-timed%dseconds' % seconds,
                         module='scripts.audit_wuji_extended_timed_commands',
                         checkpoint=str(checkpoint.relative_to(root)),
                         args=['--task', 'wuji_acquisition_official_timed2', '--hand', 'wuji_paper_official_actuator',
                               '--object', 'knife_wuji_precision_near01', '--initial-states',
                               str((out / 'initial_states.npy').relative_to(root)), '--stage-seconds', str(seconds),
                               '--total-seconds', '60', '--seed', '20261039']))
    (base / 'audit-queue-horizon60-cp100-fresh-validation.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
