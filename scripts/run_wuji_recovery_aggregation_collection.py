"""Bounded behavior/early-handover diagnostic on training states only."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--states', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'runs/artmanip-recovery-20260930' / args.name
    output.mkdir(parents=True, exist_ok=False)
    commands = []
    for seconds in [2, 5]:
        for mode in ['behavior', 'handover']:
            dest = output / f'{mode}-t{seconds}'
            cmd = [sys.executable, '-m', 'scripts.collect_wuji_recovery_aggregation',
                   '--checkpoint', args.checkpoint, '--states', args.states, '--seconds', str(seconds),
                   '--mode', mode, '--output', str(dest)]
            commands.append(cmd)
            (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            with dest.with_suffix('.log').open('w') as log:
                subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    (output / 'completed.json').write_text(json.dumps(dict(physical_episodes=512,
        control_transitions=512 * 600, scope='Training-state behavior and scripted expert-handover diagnostics, not unified success')) + '\n')


if __name__ == '__main__':
    main()
