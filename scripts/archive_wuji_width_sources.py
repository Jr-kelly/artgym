"""Per-job code overrides relative to the already public parent, no auth copies."""
import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from scripts.wuji_width_jobs import source_hash
from scripts.wuji_width_contract import sha
from scripts.record_wuji_width_goal import R,D,record


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base='89689142c9f0e52fb679ce710f9c95a55b8a6643'
    tree=subprocess.check_output(['git','ls-tree','-rz',base,'scripts','isaacgymenvs','rl_games'],cwd=R)
    objects={}
    for line in tree.split(b'\0'):
        if not line:continue
        meta,path=line.split(b'\t',1);parts=meta.split()
        if parts[1]==b'blob' and Path(path.decode()).suffix in ['.py','.yaml']:objects[path.decode()]=parts[2].decode()
    stream=subprocess.check_output(['git','cat-file','--batch'],input=('\n'.join(objects.values())+'\n').encode(),cwd=R)
    base_hash={};offset=0
    for name in objects:
        end=stream.index(b'\n',offset);size=int(stream[offset:end].split()[-1]);body=stream[end+1:end+1+size]
        base_hash[name]=hashlib.sha256(body).hexdigest();offset=end+size+2
    assert not a.output.exists();a.output.mkdir(parents=True);(a.output/'blobs').mkdir()
    entries=[]
    for receipt in sorted((R/'runs/width-student-distillation-20261002/jobs').glob('*/identity.json')):
        identity=json.loads(receipt.read_text());pin=Path('/tmp/artgym-width-local-pins')/identity['name']
        assert identity['local'] and source_hash(pin)==identity['source_sha256']
        files=[]
        for folder in ['scripts','isaacgymenvs','rl_games']:
            for path in sorted((pin/folder).rglob('*')):
                if not path.is_file() or path.suffix not in ['.py','.yaml']:continue
                rel=str(path.relative_to(pin));digest=sha(path);inherited=base_hash.get(rel)==digest
                if not inherited:
                    dest=a.output/'blobs'/digest
                    if not dest.exists():dest.write_bytes(path.read_bytes())
                files.append(dict(path=rel,sha256=digest,size=path.stat().st_size,from_public_base=inherited))
        entries.append(dict(job=identity['name'],source_sha256=identity['source_sha256'],files=files))
    manifest=dict(base_commit=base,pins=entries,recovery='Checkout public base; for each job replace files with from_public_base=false from blobs/SHA, then verify every file and ordered aggregate. Inherited historical controllers are referenced by hash, not redistributed.')
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=a.output.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tf:tf.add(a.output,arcname=a.output.name)
    report=dict(path=str(archive.resolve().relative_to(R)),sha256=sha(archive),jobs=len(entries),blobs=len(list((a.output/'blobs').iterdir())))
    (D/'SOURCE_PINS.json').write_text(json.dumps(report,indent=2)+'\n')
    record('actual_job_source_overrides_archived',evidence='research/width-student-distillation-20261002/SOURCE_PINS.json',
           next='Upload preparation packet and actual pins; no H200 training or final result exists yet')


if __name__=='__main__':main()
