"""Matched extra updates: new-state expert labels versus old-history replay."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--availability', type=Path, required=True)
    parser.add_argument('--init', type=Path, required=True)
    parser.add_argument('--end-epoch', type=int, default=6500)
    args = parser.parse_args()
    assert json.loads(args.availability.read_text())['training_allowed']
    root = Path(__file__).resolve().parents[1]
    output = root / 'runs/artmanip-recovery-20260930' / args.name
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for arm in ['replay', 'aggregate']:
        data = [str(args.data / arm / f't{seconds}/source{source}')
                for source in range(4) for seconds in [2, 5]]
        dest = output / arm / 'E'
        cmd = [sys.executable, '-m', 'scripts.train_wuji_recovery_bc', '--resume', '--init', str(args.init),
               '--data', *data, '--output', str(dest), '--label', 'executed', '--epochs', str(args.end_epoch),
               '--save-every', '100', '--lr', '.00001', '--seed', '2026093001', '--batch', '120', '--max-seconds', '800']
        (output / (arm + '-command.json')).write_text(json.dumps(cmd, indent=2) + '\n')
        with (output / (arm + '.log')).open('w') as log:
            subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=980)
        result = json.loads((dest / 'completed.json').read_text())
        assert result['epoch'] == args.end_epoch and result['updates'] == args.end_epoch * 8
        results[arm] = result
    (output / 'completed.json').write_text(json.dumps(dict(results=results,
        scope='Both arms same E5700 Adam/RNG start, batch120, data count160 with fitting120,8updates/epoch. Only20percent fitting histories differ; shared heldout40. Additional optimization and collection counted separately.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
