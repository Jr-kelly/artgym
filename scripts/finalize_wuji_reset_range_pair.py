"""Wait for all44 audited CP conditions, analyze, package and verify publication."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root, args.output
    pin = Path(__file__).resolve().parents[1]
    goal, diag = root/'runs/wuji-goal', root/'runs/wuji-goal/diagnostics'
    out.mkdir(exist_ok=False)
    state = dict(status='waiting_for_all44_audits', started=now(), pid=os.getpid(), stages=[])

    def save():
        state['heartbeat'] = now()
        atomic_json(out/'status.json', state)

    def journal(event, **fields):
        with (goal/'journal/events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(time=now(), event=event, **fields))+'\n')

    def run(name, command, timeout):
        with (out/(name+'.log')).open('w') as log:
            child = subprocess.Popen(command, cwd=pin, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            item = dict(name=name, pid=child.pid, status='running', started=now(), command=command)
            state['stages'].append(item)
            state['status'] = name
            save()
            deadline = time.monotonic()+timeout
            while child.poll() is None:
                if time.monotonic() > deadline:
                    child.terminate()
                    child.wait(timeout=20)
                    raise TimeoutError(name)
                save()
                time.sleep(15)
            item.update(status='completed' if child.returncode == 0 else 'failed', returncode=child.returncode, finished=now())
            save()
            assert child.returncode == 0, item

    save()
    try:
        deadline = time.monotonic()+86400
        while True:
            assert time.monotonic() < deadline
            monitor = json.loads((diag/'reset-range-cp-audit-monitor-20260923-v2/status.json').read_text())
            assert monitor['status'] not in ['failed', 'evaluation_failed'], monitor
            if monitor['status'] == 'completed':
                audit_path = root/monitor['last_audit']
                audit = json.loads(audit_path.read_text())
                assert audit['status'] == 'verified_complete' and audit['completed'] == audit['expected'] == 44
                break
            save()
            time.sleep(30)
        analysis = diag/'reset-range-control-analysis-final44-20260923-v2'
        run('analysis', [sys.executable, '-m', 'scripts.analyze_wuji_reset_range_pair', '--root', str(root),
                         '--audit', str(audit_path), '--output', str(analysis)], 1200)
        journal('reset_range_all44_completed_and_control_analysis_verified', audit=str(audit_path.relative_to(root)),
                analysis=str(analysis.relative_to(root)), physics_transitions=44*600*332)
        package = diag/'release-reset-range-pair-complete-20260923-v1'
        run('package', [sys.executable, '-m', 'scripts.package_wuji_reset_range_pair', '--root', str(root),
                        '--audit', str(audit_path), '--analysis', str(analysis), '--output', str(package)], 1800)
        assets = sorted(p for p in package.rglob('*') if p.is_file() and p.suffix != '.zip' and p.name != 'package-status.json')
        verification = diag/'release-reset-range-pair-complete-20260923-verified.json'
        run('publish', [sys.executable, '-m', 'scripts.resume_wuji_release_upload', '--verification', str(verification),
                        '--max-time', '300']+list(map(str, assets)), 14400)
        verified = json.loads(verification.read_text())
        assert len(verified) == len(assets) and all(item['digest_verified'] for item in verified)
        state.update(status='completed', finished=now(), verification=str(verification.relative_to(root)),
                     audit=str(audit_path.relative_to(root)), assets=len(assets))
        journal('reset_range_complete_evidence_published_and_digest_verified', **{k: state[k] for k in ['verification', 'audit', 'assets']})
        current = json.loads((goal/'goal-state.json').read_text())
        current['reset_range_complete'] = dict(status='all44_development_audits_published', audit=state['audit'],
                                               analysis=str(analysis.relative_to(goal)), verification=state['verification'],
                                               independent_success=False)
        atomic_json(goal/'goal-state.json', current)
        note = '\n\n## 自动更新：两倍扰动配对CP完整审计与发布 '+now()+'\n\n'
        note += '44/44条件正常退出并逐条复算，全部CP/两时钟/两开发集已收齐。完整分析 `'+str(analysis.relative_to(goal))+'`。'
        note += '全部 '+str(len(assets))+' 个命名Release资产已核对GitHub digest，核验 `'+str(verification.relative_to(goal))+'`。'
        note += '这是已观察开发集的完整结果，不能代替冻结后的新独立验证。\n'
        with (root/'WUJI_GOAL_HANDOFF.md').open('a') as stream:
            stream.write(note)
        shutil.copyfile(root/'WUJI_GOAL_HANDOFF.md', Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md'))
    except BaseException as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        journal('reset_range_finalization_failed', error=repr(exc), output=str(out.relative_to(root)))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
