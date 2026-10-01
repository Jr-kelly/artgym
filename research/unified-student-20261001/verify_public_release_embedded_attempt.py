"""Anonymously download published student artifacts, restore Adam/RNG and decode videos."""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from scripts.record_wuji_student_goal import R, record


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'Wuji-student-public-verification'}), timeout=120)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--download-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.download_root = args.download_root.resolve()
    args.output = args.output.resolve()
    assert not args.output.exists() and not args.download_root.exists()
    manifest = json.loads(args.manifest.read_text())
    tag = 'wuji-unified-student-20261001-v1'
    api = 'https://api.github.com/repos/Jr-kelly/artgym/releases'
    with request(api + '/tags/' + tag) as response:
        release = json.load(response)
    assert release['tag_name'] == tag and not release['draft']
    # The public release response already embeds the complete asset list.
    # Exact manifest-key equality below rejects incomplete metadata.
    assets = release['assets']
    actual = {item['name']: item for item in assets}
    expected = {item['name']: item for item in manifest['assets']}
    assert len(actual) == len(assets) and len(expected) == len(manifest['assets'])
    assert actual.keys() == expected.keys()
    for name, item in expected.items():
        assert actual[name]['state'] == 'uploaded'
        assert actual[name]['size'] == item['size']
        assert actual[name]['digest'] == 'sha256:' + item['sha256']
    frozen = json.loads((R / 'research/unified-student-20261001/final-freeze.json').read_text())
    primary = next(model for model in frozen['models'] if model['role'] == 'primary')
    assert primary['sha256'] == manifest['primary_model_sha256']
    downloads = [manifest['primary_archive']] + [video['name'] for video in manifest['videos']]
    assert len(downloads) >= 2 and len(set(downloads)) == len(downloads)
    args.download_root.mkdir(parents=True)
    record('student_public_download_started', release=release['html_url'], download_names=downloads,
           next='Verify anonymous downloaded bytes, restore primary encoder/Adam/RNG, decode every video frame')
    receipts = []
    for name in downloads:
        destination = args.download_root / name
        with request(actual[name]['browser_download_url']) as response, destination.open('xb') as stream:
            for chunk in iter(lambda: response.read(8 * 1024 * 1024), b''):
                stream.write(chunk)
        assert destination.stat().st_size == expected[name]['size']
        assert sha(destination) == expected[name]['sha256']
        receipts.append(dict(name=name, url=actual[name]['browser_download_url'],
                             sha256=sha(destination), authentication='none'))
        print(json.dumps(receipts[-1]), flush=True)
    restored = args.download_root / 'restored'
    raw = subprocess.check_output([sys.executable, '-m', 'scripts.restore_wuji_unified',
        str(args.download_root / manifest['primary_archive']), '--output', str(restored)], text=True, cwd=R)
    restore_receipt = json.loads(raw)
    checkpoint = restored / primary['path']
    assert sha(checkpoint) == primary['sha256']
    teacher = restored / frozen['teacher']['path']
    assert sha(teacher) == frozen['teacher']['sha256']
    checkpoint_receipt = args.download_root / 'downloaded-primary-restore-audit.json'
    restored_environment = dict(os.environ)
    restored_environment['CUDA_VISIBLE_DEVICES'] = ''
    restored_environment['PYTHONPATH'] = str(restored.resolve()) + ':' + str((restored / 'rl_games').resolve())
    subprocess.run([sys.executable, '-m', 'scripts.verify_wuji_student_checkpoint',
        str(checkpoint.resolve()), '--output', str(checkpoint_receipt.resolve())],
        cwd=restored, env=restored_environment, check=True)
    inference_receipt = args.download_root / 'downloaded-primary-input-audit.json'
    fixture = restored / manifest['inference_fixture_path']
    assert fixture.is_file()
    subprocess.run([sys.executable, '-m', 'scripts.audit_wuji_student_inference',
        '--student', str(checkpoint.resolve()), '--teacher', str(teacher.resolve()),
        '--probes', str(fixture.resolve()), '--output', str(inference_receipt.resolve())],
        cwd=restored, env=restored_environment, check=True)
    import imageio.v2 as imageio
    videos = []
    for specification in manifest['videos']:
        destination = args.download_root / specification['name']
        reader = imageio.get_reader(destination)
        metadata = reader.get_meta_data()
        count = 0
        try:
            for frame in reader:
                assert frame.ndim == 3 and frame.shape[2] == 3
                count += 1
        finally:
            reader.close()
        assert count == specification['frames']
        assert abs(metadata['duration'] - specification['duration_seconds']) < .2
        assert list(metadata['size']) == specification['dimensions']
        videos.append(dict(name=specification['name'], decoded_frames=count,
                           duration_seconds=metadata['duration'], dimensions=list(metadata['size']), sha256=sha(destination)))
    result = dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  release=release['html_url'], release_id=release['id'], draft=False,
                  metadata_source='anonymous public release response embedded assets', all_server_digests_verified=True, assets=len(expected), anonymous_downloads=receipts,
                  actual_restore=restore_receipt, checkpoint=json.loads(checkpoint_receipt.read_text()),
                  teacher_hash_verified=True, downloaded_code_executed=True,
                  full_policy_input_audit=json.loads(inference_receipt.read_text()), videos=videos,
                  scope='Actual public distribution, downloaded-code CPU encoder/Adam/RNG and whole-player restoration, and full video decode. This reuses the audited evaluation implementation; it is not a separate runtime implementation, new simulation or hardware result.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    record('student_public_download_restore_verified', evidence=str(args.output), release=release['html_url'],
           assets=len(expected), primary_sha256=primary['sha256'], videos=len(videos),
           next='Check final branch synchronization and owned-process cleanup before closing goal')
    print(json.dumps(dict(release=release['html_url'], assets=len(expected), videos=len(videos), restored=True)))


if __name__ == '__main__':
    main()
