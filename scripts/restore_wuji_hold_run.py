"""Restore a released hold run's weights/logs with manifest SHA verification."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('archives',type=Path,nargs='+');a=p.parse_args()
    for archive in a.archives:
        with tarfile.open(archive) as tar:
            manifest=json.load(tar.extractfile('manifest.json'));name=manifest['state']['name']
            assert Path(name).name==name
            for entry in manifest['files']:
                relative=Path(entry['path']);assert not relative.is_absolute() and '..' not in relative.parts
                assert relative.parts[:2]==('runs',name)
                target=ROOT/relative;target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():
                    member=tar.getmember(str(relative));assert member.isfile()
                    temp=target.with_name(target.name+'.download-tmp')
                    with tar.extractfile(member) as source,temp.open('wb') as dest:
                        for chunk in iter(lambda:source.read(8*1024*1024),b''):dest.write(chunk)
                    assert sha(temp)==entry['sha256'];temp.replace(target)
                assert sha(target)==entry['sha256']
            print(name,len(manifest['files']),'files SHA verified')


if __name__=='__main__':main()
