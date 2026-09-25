"""Gate the group0 wrapper, then evaluate all five frozen SAPG groups."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import hashlib
import numpy as np
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--pin', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--gpu', type=int, default=3)
    args = parser.parse_args()
    output = args.output
    assert not (output/'status.json').exists()
    output.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    atomic_json(output/'status.json', dict(status='waiting_for_gpu', started=now(), gpu=args.gpu, checkpoint_sha256=sha))
    env = runtime_environment(dict(project=str(args.pin), python=sys.executable), args.gpu)
    lease = acquire_evaluation_gpu(args.gpu)
    deadline = time.monotonic() + 1800
    while lease is None and time.monotonic() < deadline:
        time.sleep(10)
        lease = acquire_evaluation_gpu(args.gpu)
    assert lease is not None, 'GPU evaluation lease unavailable for30minutes'
    cases = []

    def run(name, group=None, preflight=False):
        folder = args.root/'runs/wuji-goal/verification'/name
        folder.mkdir(parents=True, exist_ok=True)
        assert not (folder/'status.json').exists()
        command = [sys.executable]
        if group is None:
            command += ['-m', 'scripts.audit_wuji_student_actor']
        else:
            command += [str(output/'group_source.py'), '--exploration-block', str(group)]
        seconds = 5 if name.endswith('timed5seconds') else 2
        command += ['--checkpoint', str(args.checkpoint), '--output', str(folder),
                    '--task', 'wuji_fixed_student_actor', '--hand', 'wuji_paper_official_actuator',
                    '--object', 'knife_wuji_bridge3_20260922', '--initial-states',
                    str(args.root/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
                    '--seed', '20261060', '--stage-seconds', str(seconds)]
        if preflight:
            command += ['--initial-state-rows', '0', '100', '200']
        record = dict(status='running', started=now(), command=command, gpu=args.gpu)
        with (folder/'worker.log').open('w') as log:
            child = subprocess.Popen(command, cwd=args.pin, env=env, stdout=log, stderr=subprocess.STDOUT,
                                     pass_fds=(lease.fileno(),))
            record['pid'] = child.pid
            atomic_json(folder/'status.json', record)
            try:
                code = child.wait(timeout=1800)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
                code = 124
        record.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
        atomic_json(folder/'status.json', record)
        assert code == 0, name
        assert hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() == sha
        if not preflight:
            report = json.loads((folder/'report.json').read_text())
            cases.append(dict(name=name, group=group, seconds=seconds,
                joint=[sum(x['stable_full_all_endpoints'] for x in report['records'][i:i+100]) for i in [0,100,200,300]],
                alive=[sum(x['alive_full'] for x in report['records'][i:i+100]) for i in [0,100,200,300]]))
            atomic_json(output/'results.json', cases)
        return folder

    try:
        atomic_json(output/'status.json', dict(status='preflight', started=now(), gpu=args.gpu, checkpoint_sha256=sha))
        prefix = 'frozen-student-actorrl-sigmaquarter-broad0-cp100'
        standard = run(prefix+'-block-standard-preflight-timed2seconds', preflight=True)
        wrapped = run(prefix+'-block0-preflight-timed2seconds', group=0, preflight=True)
        with np.load(standard/'trace.npz') as a, np.load(wrapped/'trace.npz') as b:
            assert set(a.files) == set(b.files)
            equality = {key: bool(np.array_equal(a[key], b[key])) for key in a.files}
        proof = dict(passed=all(equality.values()), physical_transitions=3600, equality=equality,
                     standard=str(standard), wrapped=str(wrapped), checkpoint_sha256=sha)
        atomic_json(output/'preflight.json', proof)
        assert proof['passed'], 'Group0 wrapper changed recorded physical/action trace'
        atomic_json(output/'status.json', dict(status='evaluating_all_groups', started=now(), gpu=args.gpu, checkpoint_sha256=sha))
        for group in range(5):
            for seconds in [2,5]:
                run(prefix+'-block%d-mixed332-timed%dseconds'%(group,seconds), group=group)
        assert len(cases) == 10
        atomic_json(output/'status.json', dict(status='completed', returncode=0, finished=now(),
            physical_transitions=3600+10*332*600, checkpoint_sha256=sha, reports=10,
            note='All five groups on reused development states. No newly learned weights or independent validation.'))
    except BaseException as error:
        atomic_json(output/'status.json', dict(status='failed', error=repr(error), finished=now()))
        raise
    finally:
        lease.close()


if __name__ == '__main__':
    main()
