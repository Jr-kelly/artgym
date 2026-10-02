"""Remote/local process receipt survives a lost SSH controller connection."""
import argparse
import datetime
import json
import os
import subprocess
import time
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    assert not a.receipt.exists(), 'Do not duplicate an existing execution'
    begin=time.monotonic();child=subprocess.Popen(command)
    row=dict(runner_pid=os.getpid(),child_pid=child.pid,cwd=os.getcwd(),command=command,
             cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='running')
    def save():
        tmp=a.receipt.with_suffix('.tmp');tmp.write_text(json.dumps(row,indent=2)+'\n');tmp.replace(a.receipt)
    save()
    code=child.wait();row.update(status='finished',exit_code=code,wall_seconds=time.monotonic()-begin,
                                end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
    raise SystemExit(code)


if __name__=='__main__':main()
