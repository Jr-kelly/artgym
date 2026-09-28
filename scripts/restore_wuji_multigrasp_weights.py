"""Restore released matrix weights with hash checks and adjacent epoch metadata."""
import argparse,hashlib,json,tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--downloads',type=Path,required=True);a=p.parse_args()
    for arm in 'ABCD':
        archive=a.downloads/('wuji-multigrasp-'+arm+'-checkpoints.tar.gz')
        with tarfile.open(archive) as tar:
            manifest=json.load(tar.extractfile(arm+'-weights-manifest.json'))
            assert manifest['arm']==arm and len(manifest['entries'])==4
            for entry in manifest['entries']:
                relative=Path(entry['path']);assert not relative.is_absolute() and '..' not in relative.parts
                assert relative.parts[:2]==('runs','mg_'+arm+'_seed2801')
                target=R/relative;target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():
                    member=tar.getmember(str(relative));assert member.isfile()
                    temp=target.with_suffix('.download-tmp')
                    with tar.extractfile(member) as source,temp.open('wb') as dest:
                        for block in iter(lambda:source.read(8*1024*1024),b''):dest.write(block)
                    assert sha(temp)==entry['sha256'];temp.replace(target)
                assert sha(target)==entry['sha256']
                metadata=dict(entry['metadata'],checkpoint=str(target))
                target.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
                print(arm,metadata['epoch'],entry['sha256'])
    source=a.downloads/'wuji-historical-reference.pth'
    if source.exists():
        import shutil
        assert sha(source)=='4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
        target=R/'runs/multigrasp-20260928/reference.pth';target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(source,target)
        assert sha(target)==sha(source)
    for arm in 'ABCD':
        import shutil
        source=R/'research/multigrasp-20260928/evidence'/('development-'+arm)/'frozen.json'
        target=R/'runs/multigrasp-20260928'/('development-'+arm)/'frozen.json';target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(source,target)
        assert target.read_bytes()==source.read_bytes()
if __name__=='__main__':main()
