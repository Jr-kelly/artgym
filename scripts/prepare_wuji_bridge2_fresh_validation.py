"""Prepare fresh perturbations of both training grasps after two models freeze.

The unchanged held-out grasp is appended separately, without filtering. The
20-grasp adaptation and source-plus-neighbor curriculum are compared on exactly
the same states. Their training data and learning-rate schedules differ; this is
a policy comparison, not a one-factor training ablation.
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
    models = {
        'bridge2': ('frozen-candidates/teacher-bridge2-seed36-cp50/teacher.pth',
                    '20b6276fe406fcca679e3065056a50e6625038646d802c24b389a06a6e860952'),
        'functional20': ('frozen-candidates/teacher-functional20-hemisphere-seed34-cp50/teacher.pth',
                         'bb247e2d0a704fccb3623c1e37b0728079c2b0f955547e0e187d2560ac0ace31'),
    }
    for path, digest in models.values(): assert sha(base / path) == digest
    source = root / 'caches/initial_grasp/wuji/knife_wuji_bridge2_20260922/000/train/valid_grasps.npy'
    train = np.load(source)
    assert train.shape == (2, 75)
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    out = base / 'bridge2-fresh200-each-seeds41-42'
    out.mkdir(exist_ok=False)
    pieces, splits = [], {}
    for i, label in enumerate(['source', 'novel_train']):
        states = states_for_seed(train[i:i+1], 20261041+i, hand, trials=200)
        assert np.isfinite(states).all() and len(np.unique(states, axis=0)) == 200
        path = out / (label+'.npy')
        np.save(path, states)
        pieces.append(states)
        splits[label] = dict(start=200*i, stop=200*(i+1), nominal_grasps=1, trials=200,
                             seed=20261041+i, fresh_after_models_frozen=True, sha256=sha(path))
    heldout = base / 'bridge2-evaluation-states/heldout.npy'
    pieces.append(np.load(heldout))
    splits['heldout'] = dict(start=400, stop=432, nominal_grasps=1, trials=32,
                            reused=True, sha256=sha(heldout))
    np.save(out / 'mixed432.npy', np.concatenate(pieces))
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope=__doc__,
                    splits=splits, models={key:dict(path=path, sha256=digest) for key,(path,digest) in models.items()},
                    source_sha256=sha(source), mixed_sha256=sha(out/'mixed432.npy'), no_outcome_filter=True,
                    perturbation=dict(position_per_axis_m=.0005, joint_rad=.01, rotation_vector_component_deg=.5))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (base/'bridge2-fresh-validation-proposal.json').write_text(json.dumps(manifest,indent=2)+'\n')
    jobs = []
    for key in ['bridge2','functional20']:
        for seconds in [2,5]:
            jobs.append(dict(name='%s-cp50-paired-fresh400-plus-heldout32-timed%dseconds'%(key,seconds),
                module='scripts.audit_wuji_timed_commands',checkpoint='runs/wuji-goal/'+models[key][0],
                args=['--task','wuji_acquisition_bridge_hemisphere','--hand','wuji_paper_official_actuator',
                      '--object','knife_wuji_bridge2_20260922','--initial-states',str((out/'mixed432.npy').relative_to(root)),
                      '--stage-seconds',str(seconds),'--seed','20261041']))
    (base/'audit-queue-bridge2-fresh-validation.json').write_text(json.dumps(jobs,indent=2)+'\n')
    print(json.dumps(manifest))


if __name__=='__main__':main()
