"""Anonymous release download, exact asset digests, actual weight restore and video reads."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from scripts.record_wuji_recovery import R, D, record

TAG = 'wuji-artmanip-recovery-20260930-v1'
API = 'https://api.github.com/repos/Jr-kelly/artgym/releases'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Wuji-public-artifact-verification'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download-root', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists() and not args.download_root.exists()
    release = get_json(API + '/tags/' + TAG)
    assert release['tag_name'] == TAG and not release['draft']
    assets = []
    page = 1
    while True:
        batch = get_json(API + '/' + str(release['id']) + '/assets?per_page=100&page=' + str(page))
        assets += batch
        if len(batch) < 100:
            break
        page += 1
    actual = {a['name']: a for a in assets}
    expected = {}
    for path in sorted((R / 'delivery/artmanip-recovery-20260930').glob('*.receipt.json')):
        item = json.loads(path.read_text())
        name = Path(item['archive']).name
        assert name not in expected
        expected[name] = item
    assert expected.keys() == actual.keys(), 'Published asset set must exactly match local receipts'
    for name, item in expected.items():
        asset = actual[name]
        assert asset['state'] == 'uploaded'
        assert asset['digest'] == 'sha256:' + item['sha256'] and asset['size'] == item['size']
    primary_name = 'recovery-primary-candidate-Eagg6100.tar.gz'
    downloads = [primary_name] + [n for n, e in expected.items() if e.get('kind') == 'standalone_video']
    assert len(downloads) >= 3
    args.download_root.mkdir(parents=True)
    record('public_anonymous_download_verification_started', release=release['html_url'],
           expected_assets=len(expected), download_names=downloads,
           next='Download without Authorization, hash bytes, actually restore primary and read all published demonstration videos')
    verified = []
    for name in downloads:
        target = args.download_root / name
        request = urllib.request.Request(actual[name]['browser_download_url'],
                                         headers={'User-Agent': 'Wuji-public-artifact-verification'})
        with urllib.request.urlopen(request, timeout=120) as response, target.open('xb') as stream:
            for chunk in iter(lambda: response.read(8 * 1024 * 1024), b''):
                stream.write(chunk)
        assert target.stat().st_size == expected[name]['size'] and sha(target) == expected[name]['sha256']
        verified.append(dict(name=name, sha256=sha(target), size=target.stat().st_size,
                             url=actual[name]['browser_download_url'], authentication='none'))
    restored = args.download_root / 'restored'
    raw = subprocess.check_output([sys.executable, '-m', 'scripts.restore_wuji_unified',
        str(args.download_root / primary_name), '--output', str(restored)], cwd=R, text=True)
    restore_receipt = json.loads(raw)
    import torch
    frozen = json.loads((D / 'final-freeze.json').read_text())
    model = frozen['models'][frozen['overall_candidate']]
    checkpoint = restored / model['path']
    assert sha(checkpoint) == model['sha256']
    state = torch.load(checkpoint, map_location='cpu')
    assert state['bc_epoch'] == 6100 and state['bc_updates'] == 48800
    assert all(torch.isfinite(t).all().item() for t in state['model'].values() if torch.is_tensor(t))
    adam_steps = sorted({int(s['step']) for s in state['bc_optimizer']['state'].values() if 'step' in s})
    assert adam_steps == [48800]
    assert all(k in state for k in ['bc_torch_rng', 'bc_cuda_rng', 'bc_numpy_rng'])
    import imageio.v2 as imageio
    videos = []
    for name in downloads[1:]:
        local = R / expected[name]['archive']
        metadata = json.loads(local.with_suffix('.json').read_text())
        reader = imageio.get_reader(args.download_root / name)
        count = reader.count_frames()
        video = reader.get_meta_data()
        reader.get_data(count // 2)
        reader.close()
        assert count == metadata['frame_count']
        assert abs(float(video['duration']) - metadata['duration_seconds']) < .2
        videos.append(dict(name=name, frame_count=count, duration_seconds=video['duration'],
                           decoded_middle_frame=True, sha256=metadata['sha256']))
    result = dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        release=release['html_url'], release_id=release['id'], tag=TAG, draft=False,
        asset_count=len(expected), all_server_digests_verified=True,
        assets=[dict(name=n, sha256=expected[n]['sha256'], size=expected[n]['size'],
                     url=actual[n]['browser_download_url']) for n in sorted(expected)],
        anonymous_downloads=verified, actual_restore=restore_receipt,
        checkpoint=dict(sha256=model['sha256'], epoch=6100, updates=48800,
                        adam_steps=adam_steps, finite_model=True, rng_present=True),
        videos=videos, scope='Public distribution and actual CPU restore/read verification; no new simulation or capability assessment.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    record('public_anonymous_download_restore_verified', evidence=str(args.output),
           asset_count=len(expected), checkpoint_sha256=model['sha256'], videos=len(videos),
           next='Verify final branch commit and owned-process cleanup, then close the bounded experiment')
    print(json.dumps({k: result[k] for k in ['release', 'asset_count', 'checkpoint', 'videos']}))


if __name__ == '__main__':
    main()
