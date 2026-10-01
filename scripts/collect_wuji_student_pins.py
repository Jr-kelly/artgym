"""Recover and hash actual source/config snapshots of completed jobs."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_student_goal import D, R, record
from scripts.wuji_student_jobs import REMOTE


def source_hash(root):
    digest = hashlib.sha256()
    for folder in ['scripts', 'isaacgymenvs', 'rl_games']:
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and path.suffix in ['.py', '.yaml']:
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    destination = R / 'runs/unified-student-20261001/source-pins'
    receipts = []
    skipped_legacy = []
    for result_path in sorted((R / 'runs/unified-student-20261001/jobs').glob('*/result.json')):
        identity = json.loads((result_path.parent / 'identity.json').read_text())
        name = identity['name']
        assert re.fullmatch(r'[A-Za-z0-9_-]+', name)
        expected = identity.get('pinned_source_sha256')
        expected_kind = 'recorded_actual_pin'
        if not expected and identity.get('local'):
            expected = identity.get('local_source_sha256')
            expected_kind = 'local_launch_hash_verified_against_actual_pin_now'
        if not expected:
            # Earlier snapshots were separately checked against selected-file
            # provenance. Do not invent a full hash in their job identities.
            skipped_legacy.append(name)
            continue
        target = destination / name
        if target.exists():
            assert source_hash(target) == expected, 'Existing snapshot mismatch: ' + name
            copied = False
        else:
            target.mkdir(parents=True)
            command = ['/usr/bin/rsync', '-a', '--include=*/', '--include=*.py',
                       '--include=*.yaml', '--exclude=*']
            if identity.get('local'):
                source = '/tmp/artgym-student-local-pins/' + name
            else:
                command += ['-e', '/usr/bin/ssh -i /home/agiuser/.ssh/id_ed25519_h200 -p 33024']
                source = 'wangjiarui@10.13.160.5:' + REMOTE + '/pins/' + name
            for folder in ['scripts', 'isaacgymenvs', 'rl_games']:
                subprocess.run(command + [source + '/' + folder, str(target) + '/'],
                               check=True, env=host_tool_environment())
            assert source_hash(target) == expected, 'Recovered snapshot mismatch: ' + name
            copied = True
        receipts.append(dict(name=name, source_sha256=expected, copied=copied,
                             expected_hash_provenance=expected_kind,
                             path=str(target.relative_to(R)),
                             job_identity_sha256=hashlib.sha256((result_path.parent / 'identity.json').read_bytes()).hexdigest()))
    report = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  verified=receipts, legacy_separate_audit=skipped_legacy,
                  scope='Actual immutable .py/.yaml source/config snapshots of completed jobs. '
                        'Older selected-file-only identities retain their separate prior audit; '
                        'assets and runtime dependencies are delivered separately.')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    record('completed_job_source_pins_recovered', evidence=str(args.output),
           verified=len(receipts), newly_copied=sum(r['copied'] for r in receipts),
           next='Retain snapshots for final supplemental source archive; active jobs unchanged')
    print(json.dumps(dict(verified=len(receipts), newly_copied=sum(r['copied'] for r in receipts),
                          legacy_separate_audit=len(skipped_legacy))))


if __name__ == '__main__':
    main()
