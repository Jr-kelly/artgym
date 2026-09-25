"""Finalize a complete second training seed without rerunning any physics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.host_tool_environment import host_tool_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    root, pin = Path(spec['root']), Path(__file__).resolve().parents[1]
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    training = json.loads((root/spec['training_spec']).read_text())
    state = dict(status='waiting_for_all44_audits', pid=os.getpid(), started=now(),
                 spec=spec, stages=[], source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    child = None

    def save():
        state['heartbeat'] = now()
        atomic_json(out/'status.json', state)

    def run(name, command, timeout=1800):
        nonlocal child
        with (out/(name+'.log')).open('w') as stream:
            environment = (runtime_environment(dict(project=str(pin), python=sys.executable))
                           if command[0] == sys.executable else host_tool_environment())
            child = subprocess.Popen(command, cwd=pin,
                env=environment,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        entry = dict(name=name, status='running', pid=child.pid, started=now(), command=command)
        state['stages'].append(entry)
        state['status'] = name
        stop = time.monotonic()+timeout
        while child.poll() is None:
            assert time.monotonic() < stop, name
            save()
            time.sleep(15)
        entry.update(status='completed' if child.returncode == 0 else 'failed',
                     returncode=child.returncode, finished=now())
        save()
        assert child.returncode == 0, entry

    save()
    try:
        stop = time.monotonic()+86400
        while True:
            assert time.monotonic() < stop
            path = root/spec['audit_monitor']/'status.json'
            if spec.get('remote_evaluation'):
                program = ('from pathlib import Path\nimport json\np=Path('
                           +repr(str(Path(training['root'])/spec['audit_monitor']/'status.json'))
                           +')\nprint(p.read_text() if p.exists() else "{}")\n')
                response = subprocess.run(spec['ssh']+['python3 -'], input=program, text=True,
                                          capture_output=True, timeout=40, env=host_tool_environment())
                if response.returncode:
                    state['last_access_error'] = response.stderr[-1000:]
                    save()
                    time.sleep(30)
                    continue
                monitor = json.loads(response.stdout)
                state.pop('last_access_error', None)
                state['remote_audit_status'] = monitor.get('status')
            else:
                monitor = json.loads(path.read_text()) if path.exists() else {}
            assert monitor.get('status') not in ('failed', 'evaluation_failed'), monitor
            if monitor.get('status') == 'completed':
                audit_path = root/monitor['last_audit']
                if spec.get('remote_evaluation'):
                    audit_path.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(['rsync', '-a', '-e', shlex.join(spec['ssh'][:-1]),
                                    spec['ssh'][-1]+':'+training['root']+'/'+monitor['last_audit'],
                                    str(audit_path)], check=True, timeout=120, env=host_tool_environment())
                audit = json.loads(audit_path.read_text())
                assert audit['status'] == 'verified_complete' and audit['completed'] == audit['expected'] == 44
                break
            save()
            time.sleep(30)
        state['status'] = 'sync_training_evidence'
        save()
        if spec.get('remote_evaluation'):
            jobs = json.loads((root/spec['queue']).read_text())
            assert {j['name'] for j in jobs} == set(audit['results'])
            files = set()
            for job in jobs:
                # A trailing slash requests the complete, finished result folder.
                files.add('runs/wuji-goal/verification/'+job['name']+'/')
                files.add(job['checkpoint'])
                for item in job.get('required_artifacts', []):
                    files.add(item)
                local_checkpoint = root/job['checkpoint']
                if local_checkpoint.exists():
                    assert hashlib.sha256(local_checkpoint.read_bytes()).hexdigest() == audit['results'][job['name']]['checkpoint_sha256']
                initial = root/job['args'][job['args'].index('--initial-states')+1]
                if initial.exists():
                    assert hashlib.sha256(initial.read_bytes()).hexdigest() == audit['results'][job['name']]['initial_states_sha256']
            listing = out/'evaluation-files.txt'
            listing.write_text('\n'.join(sorted(files))+'\n')
            # --recursive is explicit because --files-from changes rsync -a semantics.
            run('sync_evaluations', ['rsync', '-ar', '--files-from='+str(listing),
                '-e', shlex.join(spec['ssh'][:-1]), spec['ssh'][-1]+':'+training['root']+'/', str(root)+'/'], 1800)
            for job in jobs:
                row = audit['results'][job['name']]
                assert hashlib.sha256((root/job['checkpoint']).read_bytes()).hexdigest() == row['checkpoint_sha256']
                assert hashlib.sha256((root/'runs/wuji-goal/verification'/job['name']/'trace.npz').read_bytes()).hexdigest() == row['trace_sha256']
        # Read only remote-owned, finished training evidence. Never push status.
        program = ('from pathlib import Path\nimport json\n'
            'root=Path('+repr(training['root'])+')\n'
            'arms='+repr(training['arms'])+'\n'
            'coordinator=root/'+repr(training['output'])+'\n'
            'assert json.loads((coordinator/"status.json").read_text())["status"]=="completed"\n'
            'paths=list(coordinator.glob("*.json"))+list(coordinator.glob("*.log"))\n'
            'for arm in arms:\n'
            ' run=root/"runs"/arm["name"]\n'
            ' assert json.loads((run/"pipeline-status.json").read_text())["status"]=="completed"\n'
            ' paths += [run/n for n in ["pipeline-status.json","preflight.log","teacher.log"]]\n'
            ' paths += list((run/"summaries").rglob("*"))+list((root/arm["gate"]).glob("*"))\n'
            'print(json.dumps([str(p.relative_to(root)) for p in paths if p.is_file()]))\n')
        response = subprocess.run(spec['ssh']+['python3 -'], input=program, text=True,
                                  capture_output=True, timeout=60, check=True, env=host_tool_environment())
        files = json.loads(response.stdout)
        listing = out/'training-files.txt'
        listing.write_text('\n'.join(files)+'\n')
        subprocess.run(['rsync', '-a', '--files-from='+str(listing), '-e', shlex.join(spec['ssh'][:-1]),
                        spec['ssh'][-1]+':'+training['root']+'/', str(root)+'/'], check=True, timeout=300,
                        env=host_tool_environment())
        training_audit = root/spec['training_audit']
        run('training_audit', [sys.executable, '-m', 'scripts.audit_wuji_reset_range_training',
            '--root', str(root), '--output', str(training_audit), '--training-spec', str(root/spec['training_spec'])])
        analysis = root/spec['analysis']
        run('analysis', [sys.executable, '-m', 'scripts.analyze_wuji_reset_range_pair', '--root', str(root),
                        '--audit', str(audit_path), '--output', str(analysis)]+spec.get('analysis_args', []))
        package = root/spec['package']
        run('package', [sys.executable, '-m', 'scripts.package_wuji_reset_range_pair', '--root', str(root),
            '--audit', str(audit_path), '--analysis', str(analysis), '--output', str(package),
            '--training-spec', str(root/spec['training_spec']), '--training-audit', str(training_audit),
            '--queue', str(root/spec['queue']), '--prefix', spec['prefix']]
            +(['--description-file', str(root/spec['description_file'])] if spec.get('description_file') else []))
        assets = sorted(p for p in package.rglob('*') if p.is_file() and p.suffix != '.zip'
                        and p.name != 'package-status.json')
        verification = root/spec['verification']
        run('publish', [sys.executable, '-m', 'scripts.resume_wuji_release_upload', '--verification',
            str(verification), '--max-time', '300', '--release-id', str(spec.get('release_id', 392488331))]
            +list(map(str, assets)), 14400)
        verified = json.loads(verification.read_text())
        assert len(verified) == len(assets) and all(item['digest_verified'] for item in verified)
        state.update(status='completed', finished=now(), assets=len(assets), audit=str(audit_path.relative_to(root)),
                     verification=spec['verification'])
        event = dict(time=now(), event=spec.get('completion_event', 'second_reset_training_seed_fully_audited_and_published'),
                     analysis=spec['analysis'], verification=spec['verification'], assets=len(assets))
        with (root/'runs/wuji-goal/journal/events.jsonl').open('a') as f:
            f.write(json.dumps(event)+'\n')
        note = ('\n\n## 自动更新：'+spec.get('title', '第二训练seed完整审计')+' '+now()+'\n\n'
                '两臂训练、44条件评估和Release上传已审计。分析 `'+spec['analysis']+'`；发布核验 `'
                +spec['verification']+'`。均为已观察开发集，下一步读取两臂完整对照并冻结候选后另做新独立验证。\n')
        with (root/'WUJI_GOAL_HANDOFF.md').open('a') as f:
            f.write(note)
        shutil.copyfile(root/'WUJI_GOAL_HANDOFF.md', '/data/research/artgym/WUJI_GOAL_HANDOFF.md')
    except BaseException as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        raise
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        save()


if __name__ == '__main__':
    main()
