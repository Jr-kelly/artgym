"""Check the sigma-only PPO initialization with the frozen student controller."""
import hashlib
import json
from pathlib import Path
import sys
from scripts import check_wuji_student_actor_runtime as runtime
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'runs/wuji-goal/diagnostics/student-actorrl-sigmaquarter-runtime-v1'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    assert not (OUTPUT/'status.json').exists()
    atomic_json(OUTPUT/'status.json', dict(status='running', started=now()))
    source = 'runs/wuji-goal/frozen-candidates/student-actorrl-sigmaquarter-initial/actor.pth'
    metadata = json.loads((ROOT/Path(source).with_name('manifest.json')).read_text())
    assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest() == metadata['sha256']
    old_source, old_args = runtime.TEACHER, sys.argv
    try:
        runtime.TEACHER = source
        sys.argv = [old_args[0], '--output', str(OUTPUT/'runtime'), '--steps', '64']
        runtime.main()
        report = json.loads((OUTPUT/'runtime/report.json').read_text())
        assert report['checks']['transitions'] == 2048
        sources = report['sources']
        sources[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        atomic_json(OUTPUT/'report.json', dict(status='passed', finished=now(), sources=sources,
                    initialization=metadata, runtime=report,
                    scope='Sigma-only source transformation checked onCPU and2048realphysics transitions; no training successclaim. Broaderrewardcode uses separately recorded same-state gate.'))
        atomic_json(OUTPUT/'status.json', dict(status='completed', returncode=0, finished=now()))
    except BaseException as error:
        atomic_json(OUTPUT/'status.json', dict(status='failed', error=repr(error), finished=now()))
        raise
    finally:
        runtime.TEACHER, sys.argv = old_source, old_args


if __name__ == '__main__':
    main()
