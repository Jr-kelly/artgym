"""Bounded CPU-only final artifact pipeline; never launches or repeats simulation."""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

from scripts.record_wuji_recovery import R, D, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-seconds', type=int, default=6000)
    args = parser.parse_args()
    assert 0 < args.max_seconds <= 6000
    registration = D / 'final-archive-watch.json'
    assert not registration.exists(), 'Audit previous watcher before starting another'
    status = dict(pid=os.getpid(), started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  max_seconds=args.max_seconds, kind='CPU-only artifact orchestration', status='running')
    registration.write_text(json.dumps(status, indent=2) + '\n')
    record('final_archive_watch_started', **status,
           next='Monitor watcher receipt/log alongside final GPU jobs; it cannot launch simulation')
    start = time.monotonic()
    frozen = json.loads((D / 'final-freeze.json').read_text())
    deadline = datetime.datetime.fromisoformat(json.loads((D / 'STATE.json').read_text())['deadline_utc'])
    try:
        while time.monotonic() - start < args.max_seconds:
            assert datetime.datetime.now(datetime.timezone.utc) < deadline
            raw = subprocess.check_output([sys.executable, '-m', 'scripts.status_wuji_recovery', '--pull'], cwd=R, timeout=60)
            resource = json.loads(raw)
            assert not any(j['status'] == 'failed' for j in resource['newly_finished']), 'Review final infrastructure failure before continuing'
            changed = False
            for batch in ['final-g0', 'final-g1']:
                rows = json.loads((R / 'runs/artmanip-recovery-20260930' / batch / 'results.json').read_text())
                counts = {}
                for row in rows:
                    counts[row['model']] = counts.get(row['model'], 0) + 1
                for model, count in counts.items():
                    if count != 3:
                        continue
                    name = 'recovery-final-' + model
                    archive = R / 'delivery/artmanip-recovery-20260930' / (name + '.tar.gz')
                    receipt = archive.with_name(name + '.receipt.json')
                    restore = D / ('final-' + model + '-archive-restore.json')
                    if not receipt.exists():
                        assert not archive.exists(), 'Incomplete archive must be audited before retry'
                        subprocess.run([sys.executable, '-m', 'scripts.archive_wuji_recovery_final_model',
                            '--batch', batch, '--model', model], cwd=R, check=True, timeout=300)
                        changed = True
                    if not restore.exists():
                        with restore.with_suffix('.tmp').open('w') as output:
                            subprocess.run([sys.executable, '-m', 'scripts.restore_wuji_unified', str(archive),
                                '--output', '/tmp/wuji-recovery-final-restore'], cwd=R, stdout=output, check=True, timeout=180)
                        restore.with_suffix('.tmp').rename(restore)
                        record('final_model_archive_restore_verified', model=model,
                               evidence=str(restore.relative_to(R)), next='Upload immutable archive to draft; full independent final rescore still required')
                        changed = True
            if changed:
                subprocess.run([sys.executable, '-m', 'scripts.upload_wuji_recovery'], cwd=R, check=True, timeout=900)
            restored = [m for m in frozen['models'] if (D / ('final-' + m + '-archive-restore.json')).exists()]
            status.update(heartbeat_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          restored_models=restored, gpu_hours=resource['gpu_hours'])
            registration.write_text(json.dumps(status, indent=2) + '\n')
            print(json.dumps(dict(restored=len(restored), total=len(frozen['models']), gpu_hours=resource['gpu_hours'])), flush=True)
            if len(restored) == len(frozen['models']):
                status['status'] = 'completed'
                break
            time.sleep(45)
        else:
            raise TimeoutError('Bounded artifact watcher expired; inspect completed receipts before continuing')
    except BaseException as error:
        status.update(status='failed', error=repr(error))
        raise
    finally:
        status['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        registration.write_text(json.dumps(status, indent=2) + '\n')
        record('final_archive_watch_ended', **status,
               next='Check all18 model archives, then archive completed batch metadata and independently rescore full frozen final cohort')


if __name__ == '__main__':
    main()
