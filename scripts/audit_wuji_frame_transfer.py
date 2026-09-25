"""Matched raw/acquisition-frame evaluation on unchanged functional20 physics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from scripts import audit_wuji_extended_timed_commands as evaluator
from scripts.wuji_knife_frame import original_to_acquisition_observations


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--frame-mode', choices=['raw', 'acquisition'], required=True)
    args, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + remaining
    output = Path(remaining[remaining.index('--output') + 1])
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
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
        record['asset_sha256'] = digest
        record['slider_damping'] = float(env.object_dof_damping[0, 0])
        original = env._compute_sapg_priv_observations

        def observations():
            policy, privileged = original()
            calls[0] += 1
            if args.frame_mode == 'raw':
                return policy, privileged
            return original_to_acquisition_observations(policy, privileged)

        env._compute_sapg_priv_observations = observations
        return env, player

    evaluator.make_player = make_player
    try:
        evaluator.main()
        record.update(status='completed', observation_calls=calls[0])
    finally:
        evaluator.make_player = factory
        for path in [Path(__file__), root / 'scripts/wuji_knife_frame.py']:
            (output / path.name).write_bytes(path.read_bytes())
        record['sources'] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in [Path(__file__), root / 'scripts/wuji_knife_frame.py']}
        (output / 'frame-provenance.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
