"""Restore explicitly listed Release artifacts into a new directory."""
import argparse, datetime, hashlib, json, tarfile
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--destination',type=Path);p.add_argument('--verify-only',action='store_true');p.add_argument('--all',action='store_true',help='Also restore optional full research evidence, not needed for inference');a=p.parse_args()
    manifest=json.loads((a.manifest or a.artifacts/'release-manifest.json').read_text())
    selected=[x for x in manifest['artifacts'] if x.get('restore_default') or a.all]
    assert selected
    if not a.verify_only:
        assert a.destination is not None
        a.destination.mkdir(parents=True,exist_ok=True)
        assert not any(a.destination.iterdir()),'Restore into an empty directory'
    verified=[]
    for item in selected:
        path=a.artifacts/item['name'];assert path.is_file(),path
        assert path.stat().st_size==item['bytes'],path
        actual=digest(path);assert actual==item['sha256'],path
        if not a.verify_only and item.get('kind')=='tar.gz':
            with tarfile.open(path,'r:gz') as archive:
                assert all(not Path(x.name).is_absolute() and '..' not in Path(x.name).parts for x in archive.getmembers())
                archive.extractall(a.destination)
        verified.append(dict(name=item['name'],bytes=item['bytes'],sha256=actual))
        print(json.dumps(verified[-1]),flush=True)
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=digest(a.manifest or a.artifacts/'release-manifest.json'),verified=verified,destination=str(a.destination) if a.destination else None,verify_only=a.verify_only,scope='Artifact bytes verified and portable source/model/asset paths restored. This does not install Isaac Gym, execute physics, restore exact PhysX state, or connect hardware.')
    if not a.verify_only:(a.destination/'wuji-restore-receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))


if __name__=='__main__':main()
