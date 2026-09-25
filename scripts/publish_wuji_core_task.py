"""Publish the named core-task artifacts, preserving and verifying existing assets."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

from scripts.host_tool_environment import host_tool_environment
from scripts.monitor_wuji_checkpoints import now, atomic_json


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root/'runs/wuji-goal/release-core-teacher-student-20260924-v1'
    output = root/'runs/wuji-goal/diagnostics/release-core-teacher-student-20260924-verified.json'
    status = output.with_name('core-task-publication-status-20260924.json')
    files = sorted(folder.iterdir())
    assert files and all(p.is_file() for p in files)
    expected = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    environment = host_tool_environment()

    def release():
        return json.loads(subprocess.check_output(['gh', 'api', 'repos/Jr-kelly/artgym/releases/394720794'], env=environment))

    for attempt in range(3):
        current = release()
        assert current['tag_name'] == 'wuji-experiments-20260923'
        present = {a['name']: a for a in current['assets']}
        missing = []
        for path in files:
            if path.name in present:
                assert present[path.name].get('digest') == 'sha256:'+expected[path.name], path.name
            else:
                missing.append(str(path))
        if not missing:
            break
        atomic_json(status, dict(status='uploading', time=now(), attempt=attempt, remaining=missing))
        process = subprocess.run(['gh', 'release', 'upload', current['tag_name'], '--repo', 'Jr-kelly/artgym']+missing,
                                 env=environment, capture_output=True, text=True)
        if process.returncode:
            atomic_json(status, dict(status='retrying', time=now(), attempt=attempt, error=process.stderr))
            time.sleep(5)
    current = release()
    assets = {a['name']:a for a in current['assets']}
    verified = []
    for path in files:
        asset = assets[path.name]
        assert asset['digest'] == 'sha256:'+expected[path.name], path.name
        verified.append(dict(name=path.name, sha256=expected[path.name], asset_id=asset['id'],
                             url=asset['browser_download_url'], digest_verified=True))
    atomic_json(output, dict(time=now(), release=current['html_url'], artifacts=verified))
    atomic_json(status, dict(status='completed', time=now(), verified_assets=len(verified)))
    print(json.dumps(dict(release=current['html_url'], verified_assets=len(verified))))


if __name__ == '__main__':
    main()
