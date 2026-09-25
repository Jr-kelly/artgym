"""Restore the archived private generator runtime if node-local /tmp is cleared."""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import os

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path('/tmp/artgym-lygra-runtime')


def ensure_runtime():
    python=RUNTIME/'bin/python'
    marker=RUNTIME/'.artgym-verified'
    if marker.exists() and python.exists():return str(python)
    with Path('/tmp/artgym-experiments-20260921-runtime.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if marker.exists() and python.exists():return str(python)
        metadata=json.loads((ROOT/'runtimes/lygra-runtime.json').read_text())
        archive=Path(metadata['archive'])
        digest=hashlib.sha256()
        with archive.open('rb') as stream:
            for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=metadata['sha256']:raise ValueError('Runtime archive checksum mismatch')
        RUNTIME.mkdir(exist_ok=True)
        subprocess.run(['tar','-xzf',str(archive),'-C',str(RUNTIME)],check=True)
        env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None)
        subprocess.run([str(python),'-c','import torch, hydra, open3d, scipy'],env=env,check=True)
        marker.write_text(metadata['sha256'])
    return str(python)


if __name__=='__main__':print(ensure_runtime())
