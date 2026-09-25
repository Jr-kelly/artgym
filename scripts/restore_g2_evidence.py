"""Restore and verify one historical G2 source pin from the incremental bundle."""
import argparse,hashlib,json,shutil,subprocess,tarfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--trial',required=True)
    p.add_argument('--repo',type=Path,default=Path.cwd());p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    trial=a.evidence/'trials'/a.trial;mapping=json.loads((trial/'source-overrides.json').read_text())
    a.output.mkdir(parents=True,exist_ok=False)
    child=subprocess.Popen(['git','archive',mapping['base_commit']],cwd=a.repo,stdout=subprocess.PIPE)
    with tarfile.open(fileobj=child.stdout,mode='r|') as archive:archive.extractall(a.output)
    if child.wait()!=0:raise RuntimeError('git archive failed')
    for name,sha in mapping['overrides'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Invalid relative source path')
        source=a.evidence/'sources/blobs'/sha
        if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:raise ValueError('Corrupt source blob '+sha)
        destination=a.output/path;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    manifest=json.loads((trial/'SOURCE_SHA256.json').read_text());errors=[]
    for name,sha in manifest.items():
        file=a.output/name
        if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest()!=sha:errors.append(name)
    if errors:raise ValueError('Source manifest mismatches: '+str(errors))
    shutil.copyfile(trial/'SOURCE_SHA256.json',a.output/'SOURCE_SHA256.json')
    print(json.dumps(dict(trial=a.trial,verified_files=len(manifest),restored=str(a.output))))


if __name__=='__main__':main()
