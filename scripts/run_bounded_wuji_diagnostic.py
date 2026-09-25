"""Run one diagnostic with a finite deadline and preserve its actual exit status."""
import argparse
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--gpu',type=int,required=True)
    p.add_argument('--timeout',type=int,default=1800)
    p.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args();root=Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'status.json').exists()
    command=args.command[1:] if args.command[0]=='--' else args.command
    assert command
    env=runtime_environment(dict(project=str(root),python=sys.executable),args.gpu)
    with (args.output/'worker.log').open('w') as log:
        child=subprocess.Popen([sys.executable]+command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    state=dict(status='running',pid=child.pid,started=now(),command=command,gpu=args.gpu)
    atomic_json(args.output/'status.json',state)
    try:code=child.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:child.kill();child.wait();code=124
    state.update(status='completed' if code==0 else 'failed',finished=now(),returncode=code)
    atomic_json(args.output/'status.json',state)
    raise SystemExit(code)


if __name__=='__main__':main()
