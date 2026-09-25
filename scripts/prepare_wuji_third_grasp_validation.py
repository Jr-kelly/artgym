"""Freeze a fresh third training-grasp cohort without filtering outcomes.

Row15 was selected using the functional20 training-only CP100 results (4/4).
It is not an unseen-grasp test of that policy. The bridge2 continuation excluded
this row, but no claim about its entire ancestor's training exposure is made.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    models = {
        'functional20-cp100': ('teacher-functional20-hemisphere-seed34-cp100', 'd44f5c6f49ed5661af33e0acc226bc1072ee74f316893c26ae6d512cca05a41d'),
        'bridge2-cp50': ('teacher-bridge2-seed36-cp50', '20b6276fe406fcca679e3065056a50e6625038646d802c24b389a06a6e860952'),
    }
    for name, digest in models.values():
        assert hashlib.sha256((base / 'frozen-candidates' / name / 'teacher.pth').read_bytes()).hexdigest() == digest
    source = root / 'caches/initial_grasp/wuji/knife_wuji_lowgain_functional20_20260922/000/train/valid_grasps.npy'
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    states = states_for_seed(np.load(source)[15:16], 20261044, hand, trials=200)
    assert states.shape == (200, 75) and np.isfinite(states).all()
    output = base / 'functional15-fresh200-seed20261044'
    output.mkdir(exist_ok=False)
    np.save(output / 'initial_states.npy', states)
    manifest = dict(scope=__doc__, training_row=15, nominal_grasps=1, perturbations=200, seed=20261044,
                    no_outcome_filter=True, frozen_models=models,
                    states_sha256=hashlib.sha256((output / 'initial_states.npy').read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    perturbations_units=dict(position_per_axis_m=.0005, joint_rad=.01, rotation_vector_component_deg=.5))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (base / 'third-grasp-validation-proposal.json').write_text(json.dumps(manifest, indent=2) + '\n')
    jobs = []
    for key, (name, _) in models.items():
        for seconds in [2, 5]:
            jobs.append(dict(name='functional15-%s-fresh200-seed44-timed%dseconds' % (key, seconds),
                             module='scripts.audit_wuji_timed_commands',
                             checkpoint='runs/wuji-goal/frozen-candidates/' + name + '/teacher.pth',
                             args=['--task', 'wuji_acquisition_bridge_hemisphere', '--hand', 'wuji_paper_official_actuator',
                                   '--object', 'knife_wuji_bridge2_20260922', '--initial-states', str((output / 'initial_states.npy').relative_to(root)),
                                   '--stage-seconds', str(seconds), '--seed', '20261044']))
    (base / 'audit-queue-third-grasp-validation.json').write_text(json.dumps(jobs, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
