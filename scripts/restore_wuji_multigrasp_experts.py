"""Restore released single-grasp expert checkpoints, verifying every weight hash."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--rows', nargs='+', type=int, choices=[3, 5, 11], default=[3, 5, 11])
    args = parser.parse_args()
    for row in args.rows:
        name = f'expert_row{row}_seed2810'
        with tarfile.open(args.downloads / f'wuji-expert-{row}-checkpoints.tar.gz') as archive:
            manifest = json.load(archive.extractfile(f'expert-{row}-manifest.json'))
            assert manifest['state']['name'] == name and manifest['state']['status'] == 'completed'
            assert {entry['epoch'] for entry in manifest['entries']} == {250, 500, 750, 1000}
            for entry in manifest['entries']:
                relative = Path(entry['path'])
                assert relative == Path('runs') / name / 'checkpoints' / f"epoch_{entry['epoch']:06d}.pth"
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    member = archive.getmember(str(relative))
                    assert member.isfile()
                    temporary = target.with_suffix('.download-tmp')
                    with archive.extractfile(member) as source, temporary.open('wb') as destination:
                        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
                            destination.write(chunk)
                    assert sha(temporary) == entry['sha256']
                    temporary.replace(target)
                assert sha(target) == entry['sha256']
                metadata = target.with_suffix('.json')
                if not metadata.exists():
                    metadata.write_text(json.dumps(dict(entry['metadata'], checkpoint=str(target)), indent=2) + '\n')
                saved = json.loads(metadata.read_text())
                assert saved['epoch'] == entry['epoch'] and saved['frame'] == entry['frame']
                print(row, entry['epoch'], entry['sha256'])


if __name__ == '__main__':
    main()
