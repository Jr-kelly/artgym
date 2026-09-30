"""Pull and archive one completed frozen model while other final models run."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.launch_wuji_recovery import R, D, REMOTE
from scripts.record_wuji_recovery import record


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', choices=['final-g0', 'final-g1'], required=True)
    parser.add_argument('--model', required=True)
    args = parser.parse_args()
    frozen_path = D / 'final-freeze.json'
    frozen = json.loads(frozen_path.read_text())
    assert args.model in frozen['models']
    batch = Path('runs/artmanip-recovery-20260930') / args.batch
    plan = json.loads((R / batch / 'plan.json').read_text())
    assert plan['freeze_sha256'] == sha(frozen_path)
    results = json.loads((R / batch / 'results.json').read_text())
    selected = [x for x in results if x['model'] == args.model]
    assert len(selected) == 3 and {x['protocol'] for x in selected} == {'S2', 'S5', 'F'}
    assert all(x['report']['checkpoint_sha256'] == frozen['models'][args.model]['sha256']
               and x['report']['initial_states_sha256'] == frozen['final_states']['sha256']
               and x['report']['num_envs'] == 512 for x in selected)
    name = 'recovery-final-' + args.model
    assert not (R / 'delivery/artmanip-recovery-20260930' / (name + '.tar.gz')).exists()
    paths = [batch / (args.model + '-' + protocol + suffix)
             for protocol in ['S2', 'S5', 'F'] for suffix in ['', '.log']]
    record('completed_final_model_pull_started', model=args.model, batch=args.batch,
           checkpoint_sha256=frozen['models'][args.model]['sha256'],
           next='Pull immutable completed physical cells; full final independent rescore still required')
    ssh = 'ssh -i /home/agiuser/.ssh/id_ed25519_h200 -p 33024'
    sources = ['wangjiarui@10.13.160.5:' + REMOTE + '/' + str(p) for p in paths]
    subprocess.run(['rsync', '-a', '-e', ssh, *sources, str(R / batch) + '/'], check=True)
    for item in selected:
        directory = R / batch / item['directory']
        assert json.loads((directory / 'report.json').read_text()) == item['report']
        assert (directory / 'trace.npz').is_file()
    subprocess.run([sys.executable, '-m', 'scripts.archive_wuji_recovery', '--name', name,
                    '--paths', *map(str, paths), str(batch / 'plan.json'),
                    'research/artmanip-recovery-20260930/final-freeze.json'], cwd=R, check=True)
    record('completed_final_model_archived', model=args.model, archive=name + '.tar.gz',
           next='Restore-check and upload to draft; final audit must still cover all18 models and54 physical cells')


if __name__ == '__main__':
    main()
