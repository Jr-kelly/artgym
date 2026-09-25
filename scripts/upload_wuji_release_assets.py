"""Upload named evidence assets to the user-authorized ArtGym release, verifying SHA256."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import quote
from scripts.host_tool_environment import host_tool_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verification', type=Path, required=True)
    parser.add_argument('--max-time', type=int, default=300, help='Per-asset upload timeout in seconds.')
    parser.add_argument('--release-id', type=int, default=392488331)
    parser.add_argument('assets', type=Path, nargs='+')
    args = parser.parse_args()
    assert args.max_time > 0
    assert not args.verification.exists()
    assert len({p.name for p in args.assets}) == len(args.assets)
    token = subprocess.check_output(['gh', 'auth', 'token'], text=True, env=host_tool_environment()).strip()
    assert token and not any(c in token for c in '\n\r"')
    records = []
    for asset in args.assets:
        assert asset.is_file()
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='artgym-release-') as temporary:
            response = Path(temporary) / 'response.json'
            uploaded = subprocess.run([
                'curl', '-4', '--silent', '--show-error', '--fail-with-body', '--http1.1',
                '--connect-timeout', '8', '--max-time', str(args.max_time), '--config', '-',
                '--header', 'Content-Type: application/octet-stream',
                '--data-binary', '@' + str(asset.resolve()), '-o', str(response),
                f'https://uploads.github.com/repos/Jr-kelly/artgym/releases/{args.release_id}/assets?name=' + quote(asset.name),
            ], input='header = "Authorization: Bearer ' + token + '"\n', text=True, env=host_tool_environment())
            if uploaded.returncode:
                if response.exists():
                    args.verification.with_suffix('.error.json').write_bytes(response.read_bytes())
                uploaded.check_returncode()
            result = json.loads(response.read_text())
        assert result['digest'] == 'sha256:' + digest
        records.append(dict(name=asset.name, sha256=digest, asset_id=result['id'],
                            url=result['browser_download_url'], digest_verified=True))
        print(json.dumps(records[-1]), flush=True)
        # Partial progress is recoverable without overwriting public assets.
        pending = args.verification.with_suffix('.pending.json')
        pending.write_text(json.dumps(records, indent=2) + '\n')
    pending.replace(args.verification)


if __name__ == '__main__':
    main()
