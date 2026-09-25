"""Physical validation and provenance for generated Wuji paper grasp candidates.

Run inside the Isaac Gym artgym environment, after Lightning Grasp generation.
The validator writes full states using ArtGym's original contact/stability test.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'caches/initial_grasp/wuji/knife_wuji_paper'


def fingerprint(paths):
    result = hashlib.sha256()
    for path in paths:
        result.update(path.read_bytes())
    return result.hexdigest()


def check_dataset(require_test=True, minimum_train=10):
    """Fail closed: ArtManip otherwise silently omits instances with no cache."""
    manifest = json.loads((ROOT/'assets/objects/knife_wuji_paper/manifest.json').read_text())
    rows = []
    for instance in manifest['train_ids']+(manifest['test_ids'] if require_test else []):
        folder = CACHE/instance
        candidates = json.loads((folder/'candidate_manifest.json').read_text())
        validation = json.loads((folder/'validation_manifest.json').read_text())
        if candidates['unique_candidates'] < 1000:
            raise ValueError(f'{instance}: paper protocol requires 1000 unique candidates')
        if candidates['field_samples'] < 80000:
            raise ValueError(f'{instance}: debug contact field cannot enter training')
        assets = ROOT/'assets/objects/knife_wuji_paper'/instance
        inputs = [folder/'qpos.npy', folder/'opos.npy', folder/'candidate_manifest.json', assets/'mobility.urdf']
        if validation['input_sha256'] != fingerprint(inputs):
            raise ValueError(f'{instance}: validation is stale relative to candidates/assets')
        if validation['valid'] == 0:
            raise ValueError(f'{instance}: no physically valid grasps')
        if validation.get('hand_config') != 'wuji_paper' or validation['steps'] < 30:
            raise ValueError(f'{instance}: expected filtered self-collision and at least one second of physical validation')
        if instance in manifest['train_ids'] and validation['train'] < minimum_train:
            raise ValueError(f'{instance}: fewer than {minimum_train} training grasps; regenerate before training')
        for split in ('train', 'test'):
            data = np.load(folder/split/'valid_grasps.npy', allow_pickle=False)
            if data.ndim != 2 or data.shape[1] != 75 or not np.isfinite(data).all():
                raise ValueError(f'{instance}/{split}: malformed full grasp state')
        rows.append(dict(instance=instance, **validation))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instances', nargs='+', default=['all'])
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--steps', type=int, default=30, help='30 control steps = 1 second')
    parser.add_argument('--check-training-ready', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.check_training_ready:
        rows = check_dataset()
        print('All 35 instances validated; training uses only 000–029.', flush=True)
        print(json.dumps(rows, indent=2))
        return
    manifest = json.loads((ROOT/'assets/objects/knife_wuji_paper/manifest.json').read_text())
    instances = manifest['train_ids']+manifest['test_ids'] if args.instances == ['all'] else args.instances
    for instance in instances:
        folder = CACHE/instance
        q = np.load(folder/'qpos.npy', allow_pickle=False)
        if q.ndim != 2 or q.shape[1] != 20 or not len(q) or not np.isfinite(q).all():
            raise ValueError(f'{instance}: malformed candidate joint states')
        assets = ROOT/'assets/objects/knife_wuji_paper'/instance
        signature = fingerprint([folder/'qpos.npy', folder/'opos.npy', folder/'candidate_manifest.json', assets/'mobility.urdf'])
        output = folder/'validation_manifest.json'
        if output.exists():
            previous = json.loads(output.read_text())
            if (previous['input_sha256'] == signature and previous['steps'] == args.steps
                    and previous.get('hand_config') == 'wuji_paper' and previous['valid'] > 0):
                print(instance, 'already validated', previous['valid'], flush=True)
                continue
        # No duplicated padding samples are added to make a batch divisible.
        batch = math.gcd(len(q), args.batch_size)
        command = [sys.executable, '-m', 'isaacgymenvs.valid_grasp', '--hand', 'wuji_paper',
                   '--object', 'knife_wuji_paper', '--instance-id', instance, '--pipeline', 'cpu',
                   '--num-envs', str(batch), '--episode-length', str(args.steps), '--headless',
                   '--seed', '20260920', '--override', 'task.env.forceScale=0']
        log = ROOT/'tmp/paper-grasps'/f'validate-{instance}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        print(instance, 'validating', len(q), 'candidates; log:', log, flush=True)
        started = time.time()
        with log.open('w') as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
        counts = {}
        for key, relative in [('valid','valid_grasps.npy'), ('train','train/valid_grasps.npy'), ('test','test/valid_grasps.npy')]:
            data = np.load(folder/relative, allow_pickle=False)
            counts[key] = len(data)
        report = dict(input_sha256=signature, candidates=len(q), steps=args.steps,
                      simulated_seconds=args.steps*4/120, gravity=True, contact_num=5, hand_config='wuji_paper',
                      pos_threshold_m=.05, rot_threshold_rad=1.57, force_scale=0,
                      seconds=time.time()-started, command=command, **counts)
        output.write_text(json.dumps(report, indent=2))
        print(instance, counts, flush=True)
        if not counts['valid']:
            raise RuntimeError(f'{instance}: zero stable functional grasps; inspect {log}')


if __name__ == '__main__':
    main()
