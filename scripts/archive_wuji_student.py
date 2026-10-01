"""Hash, archive, and verify explicitly completed evidence; no mutation of sources."""
import argparse,hashlib,json,tarfile,io,datetime
from pathlib import Path
from scripts.record_wuji_student_goal import record,R,D

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--paths',nargs='+',required=True);a=p.parse_args()
    dest=R/'delivery/unified-student-20261001';dest.mkdir(parents=True,exist_ok=True);archive=dest/(a.name+'.tar.gz');assert not archive.exists()
    files=[]
    for rel in a.paths:
        path=R/rel;assert path.exists();files.extend([path] if path.is_file() else [x for x in path.rglob('*') if x.is_file() and not x.is_symlink()])
    files=sorted(x for x in set(files) if not {'.git','__pycache__','.pytest_cache'}.intersection(x.relative_to(R).parts) and x.suffix not in {'.pyc','.pyo'})
    entries=[dict(path=str(x.relative_to(R)),sha256=sha(x),size=x.stat().st_size) for x in files]
    record('archive_started',name=a.name,paths=a.paths,next='Verify source hashes then upload independent release asset')
    manifest=dict(name=a.name,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=entries,restore='python -m scripts.restore_wuji_unified ARCHIVE --output RESTORE_ROOT')
    with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
        raw=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('release-manifests/'+a.name+'.json');info.size=len(raw);tf.addfile(info,io.BytesIO(raw))
        for x,e in zip(files,entries):tf.add(x,arcname=e['path'],recursive=False);assert sha(x)==e['sha256']
    receipt=dict(name=a.name,archive=str(archive.relative_to(R)),sha256=sha(archive),size=archive.stat().st_size,files=len(entries));(dest/(a.name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    record('archive_completed',**receipt,next='Restore-check and upload; local originals retained');print(json.dumps(receipt))
if __name__=='__main__':main()
