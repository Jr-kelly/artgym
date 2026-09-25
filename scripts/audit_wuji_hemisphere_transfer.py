"""Matched acquisition-frame/hemisphere evaluation on unchanged functional20 physics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from scripts import audit_wuji_extended_timed_commands as evaluator
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
import numpy as np


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--frame-mode', choices=['acquisition', 'acquisition_hemisphere'], required=True)
    args, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + remaining
    output = Path(remaining[remaining.index('--output') + 1])
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    source = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == '056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5'
    reference = np.load(source)[0, 43:47]
    factory = evaluator.make_player
    calls = [0]
    record = dict(mode=args.frame_mode, scope=__doc__, observation_calls=0)

    def make_player(cfg, checkpoint):
        env, player = factory(cfg, checkpoint)
        assert not any(arg == '--student-artifact' for arg in remaining)
        assert env.object_cfg['asset']['asset_root'] == 'assets/objects/knife_wuji_lowgain_functional20_20260922'
        asset = root / env.object_cfg['asset']['asset_root'] / '000/mobility.urdf'
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        assert digest == '5229c66b183cc6da04190bf2d6cfbd035fadd227340dc8f26602b207171b461c'
        assert ET.parse(asset).find(".//joint[@name='slider']/axis").get('xyz') == '0 0 1'
        assert abs(float(env.object_dof_damping[0, 0]) - .3) < 1e-6
        record['reference_training_state_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        record['reference_quaternion'] = reference.tolist()
        record['asset_sha256'] = digest
        record['slider_damping'] = float(env.object_dof_damping[0, 0])
        original = env._compute_sapg_priv_observations

        def observations():
            policy, privileged = original()
            calls[0] += 1
            policy, privileged = original_to_acquisition_observations(policy, privileged)
            if args.frame_mode == 'acquisition_hemisphere':
                return align_quaternion_hemisphere(policy, privileged, reference)
            return policy, privileged

        env._compute_sapg_priv_observations = observations
        return env, player

    evaluator.make_player = make_player
    try:
        evaluator.main()
        record.update(status='completed', observation_calls=calls[0])
    finally:
        evaluator.make_player = factory
        for path in [Path(__file__), root / 'scripts/wuji_knife_frame.py', root / 'scripts/wuji_quaternion_hemisphere.py']:
            (output / path.name).write_bytes(path.read_bytes())
        record['sources'] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in [Path(__file__), root / 'scripts/wuji_knife_frame.py', root / 'scripts/wuji_quaternion_hemisphere.py']}
        (output / 'frame-provenance.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
