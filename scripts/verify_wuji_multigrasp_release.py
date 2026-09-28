"""Verify published release assets against upload SHA receipts and record public URLs."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-id', type=int, default=398592814)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-draft', action='store_true')
    args = parser.parse_args()
    release = json.loads(subprocess.check_output(['gh', 'api', f'repos/Jr-kelly/artgym/releases/{args.release_id}'], text=True))
    assert release['tag_name'] == 'wuji-multigrasp-20260928-v1'
    assert args.allow_draft or not release['draft']
    expected = {}
    for path in (ROOT / 'research/multigrasp-20260928/receipts').glob('release-*.json'):
        if path.name.endswith(('.pending.json', '.error.json')):
            continue
        records = json.loads(path.read_text())
        if not isinstance(records, list):
            continue
        for record in records:
            assert record['digest_verified']
            if record['name'] in expected:
                assert expected[record['name']] == record['sha256']
            expected[record['name']] = record['sha256']
    actual = {asset['name']: asset for asset in release['assets']}
    assert actual.keys() == expected.keys(), (sorted(actual.keys()-expected.keys()), sorted(expected.keys()-actual.keys()))
    assets = []
    for name in sorted(expected):
        asset = actual[name]
        assert asset['state'] == 'uploaded' and asset['digest'] == 'sha256:' + expected[name]
        if not release['draft']:
            assert '/download/wuji-multigrasp-20260928-v1/' in asset['browser_download_url']
        assets.append(dict(name=name, bytes=asset['size'], sha256=expected[name],
                           url=asset['browser_download_url'], server_digest_verified=True))
    output = dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  release_id=release['id'], tag=release['tag_name'], draft=release['draft'],
                  url=release['html_url'], asset_count=len(assets), assets=assets)
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(dict(asset_count=len(assets), draft=release['draft'], url=release['html_url'])))


if __name__ == '__main__':
    main()
