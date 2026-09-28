"""Bounded read-only remote collector for the three already-running experts."""
import datetime
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from scripts.monitor_wuji_multigrasp_round import SSH, REMOTE

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs/multigrasp-20260928'
RESEARCH = ROOT / 'research/multigrasp-20260928'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sync(relative):
    target = ROOT / relative
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(['rsync', '-a', '-e', shlex.join(SSH[:-1]),
                    SSH[-1] + ':' + REMOTE + '/' + relative + '/', str(target) + '/'],
                   check=True, timeout=600)


def event(name, summary, evidence):
    subprocess.run([sys.executable, '-m', 'scripts.record_wuji_multigrasp_event',
                    '--event', name, '--summary', summary, '--evidence', str(evidence),
                    '--next', 'Complete expert independent rescore and final GitHub delivery'],
                   cwd=ROOT, check=True)


def main():
    import torch
    done = set()
    trained = set()
    deadline = datetime.datetime(2026, 9, 29, 1, 0, tzinfo=datetime.timezone.utc)
    while datetime.datetime.now(datetime.timezone.utc) < deadline:
        for row in (3, 5, 11):
            if row in done:
                continue
            name = f'expert_row{row}_seed2810'
            code = f"import json,pathlib; r=pathlib.Path({REMOTE!r}); s=json.loads((r/'runs/multigrasp-20260928/{name}/status.json').read_text()); print(json.dumps(dict(state=s,evaluated=(r/'runs/multigrasp-20260928/{name}-evaluation/results.json').exists())))"
            observed = json.loads(subprocess.check_output(SSH + ['python3 -c ' + shlex.quote(code)], text=True, timeout=30))
            state = observed['state']
            if state['status'] == 'failed':
                raise RuntimeError(state)
            if state['status'] == 'completed' and row not in trained:
                sync('runs/multigrasp-20260928/' + name)
                sync('runs/' + name + '/checkpoints')
                entries = []
                for epoch in (250, 500, 750, 1000):
                    path = ROOT / 'runs' / name / 'checkpoints' / f'epoch_{epoch:06d}.pth'
                    checkpoint = torch.load(path, map_location='cpu')
                    rank = checkpoint[0] if 0 in checkpoint else checkpoint
                    assert rank['epoch'] == epoch and rank['frame'] == epoch * 163840
                    assert all(not t.is_floating_point() or torch.isfinite(t).all().item() for t in rank['model'].values())
                    digest = sha(path)
                    remote = subprocess.check_output(SSH + ['sha256sum ' + shlex.quote(REMOTE + '/' + str(path.relative_to(ROOT)))], text=True).split()[0]
                    assert digest == remote
                    entries.append(dict(path=str(path.relative_to(ROOT)), sha256=digest,
                                        epoch=epoch, frame=rank['frame'], finite=True,
                                        optimizer_saved='optimizer' in rank,
                                        metadata=json.loads(path.with_suffix('.json').read_text())))
                receipt = RESEARCH / 'receipts' / f'expert-{row}-complete.json'
                receipt.write_text(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), state=state, entries=entries), indent=2) + '\n')
                shutil.copytree(RUNS / name, RESEARCH / 'evidence' / name, dirs_exist_ok=True)
                archive = RUNS / 'delivery' / f'wuji-expert-{row}-checkpoints.tar.gz'
                with tarfile.open(archive, 'x:gz') as tar:
                    tar.add(receipt, arcname=f'expert-{row}-manifest.json')
                    for entry in entries:
                        tar.add(ROOT / entry['path'], arcname=entry['path'])
                        metadata = (ROOT / entry['path']).with_suffix('.json')
                        tar.add(metadata, arcname=str(metadata.relative_to(ROOT)))
                trained.add(row)
                event(f'expert_{row}_training_complete', f'Source {row}: final1000 complete; all four checkpoints remote/local SHA and CPU epoch/frame/finite checks passed.', receipt)
            if observed['evaluated']:
                sync('runs/multigrasp-20260928/' + name + '-evaluation')
                for protocol in ('static', 'fixed2', 'fixed5', 'arrival'):
                    sync('runs/multigrasp-20260928/' + name + '-' + protocol)
                    shutil.copytree(RUNS / (name + '-' + protocol), RESEARCH / 'evidence' / (name + '-' + protocol),
                                    ignore=shutil.ignore_patterns('trace.npz'), dirs_exist_ok=True)
                shutil.copytree(RUNS / (name + '-evaluation'), RESEARCH / 'evidence' / (name + '-evaluation'), dirs_exist_ok=True)
                output = RESEARCH / 'expert-analysis' / f'row{row}'
                subprocess.run([sys.executable, '-m', 'scripts.analyze_wuji_multigrasp_experts', '--results',
                                str(RUNS / (name + '-evaluation') / 'results.json'), '--output', str(output)], cwd=ROOT, check=True)
                archive = RUNS / 'delivery' / f'wuji-expert-{row}-raw-evidence.tar.gz'
                with tarfile.open(archive, 'x:gz') as tar:
                    for suffix in ('-evaluation', '-static', '-fixed2', '-fixed5', '-arrival'):
                        directory = RUNS / (name + suffix)
                        tar.add(directory, arcname=str(directory.relative_to(ROOT)))
                done.add(row)
                event(f'expert_{row}_evaluation_complete', f'Source {row}: static and three policy protocols complete, 96 policy trials independently rescored; see per-source results.', output / 'report.json')
        if len(done) == 3:
            return
        time.sleep(30)
    raise TimeoutError(f'Collector deadline reached; trained={trained}, evaluated={done}')


if __name__ == '__main__':
    main()
