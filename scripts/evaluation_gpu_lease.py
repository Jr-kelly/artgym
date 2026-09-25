"""One evaluation owner per physical GPU on this host, across all queues.

Training may share its GPU with one evaluation. Legacy evaluators without a
lease are detected from their process environment so rollout jobs can finish
before a newly coordinated job starts. Locks live in /tmp, not shared GPFS.
"""
import fcntl
import os
from pathlib import Path


def legacy_evaluators(gpu):
    found = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            command = (process / 'cmdline').read_bytes().split(b'\0')
            modules = {part.decode(errors='replace') for part in command}
            evaluating = ('isaacgymenvs.eval_consecutive' in modules or
                          any(part.startswith('scripts.audit_wuji_') for part in modules))
            if not evaluating:
                continue
            environment = dict(part.split(b'=', 1) for part in (process / 'environ').read_bytes().split(b'\0') if b'=' in part)
            if environment.get(b'CUDA_VISIBLE_DEVICES') == str(gpu).encode():
                found.append(int(process.name))
        except (OSError, ValueError):
            continue
    return found


def acquire_evaluation_gpu(gpu):
    """Nonblocking lease. Close the file to release; never explicitly unlock.

    A launcher may pass its fd into an evaluation worker with pass_fds, then
    close its own copy. The worker retains the lock until its process exits.
    """
    path = Path('/tmp') / ('artgym-evaluation-gpu-%d-%d.lock' % (os.getuid(), int(gpu)))
    stream = path.open('a+')
    try:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        return None
    if legacy_evaluators(gpu):
        stream.close()
        return None
    return stream
