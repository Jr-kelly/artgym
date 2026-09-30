"""Bounded read-only workstation utilization samples during fixed video rendering."""
import argparse
import datetime
import json
import os
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-seconds', type=int, default=1800)
    args = parser.parse_args()
    assert 0 < args.max_seconds <= 1800 and not args.output.exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    deadline = datetime.datetime.fromisoformat('2026-09-30T22:42:33+00:00')
    with args.output.open('x') as stream:
        while time.monotonic() - start < args.max_seconds and datetime.datetime.now(datetime.timezone.utc) < deadline:
            sample_start = time.monotonic()
            try:
                result = subprocess.check_output(['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used',
                    '--format=csv,noheader'], text=True, timeout=10)
                row = dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           host='local', sampler_pid=os.getpid(), gpus=result)
            except (subprocess.SubprocessError, OSError) as error:
                row = dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), error=repr(error))
            stream.write(json.dumps(row) + '\n')
            stream.flush()
            time.sleep(max(.1, 5 - (time.monotonic() - sample_start)))


if __name__ == '__main__':
    main()
