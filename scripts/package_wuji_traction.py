"""Build a small portable overlay and selected evidence, excluding private media."""
import argparse,hashlib,json,tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=Path('runs/traction-20261005');D=Path('research/traction-20261005')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packet(output,name,files):
    rows=[dict(path=str(p),bytes=(R/p).stat().st_size,sha256=digest(R/p)) for p in sorted(set(files))]
    manifest=output/(name+'-files.json');manifest.write_text(json.dumps(dict(files=rows),indent=2))
    path=output/(name+'.tar.gz')
    with tarfile.open(path,'w:gz',dereference=True) as tar:
        for row in rows:tar.add(R/row['path'],arcname=row['path'],recursive=False)
        tar.add(manifest,arcname='recovery-manifests/'+manifest.name)
    return dict(name=path.name,sha256=digest(path),bytes=path.stat().st_size,files=len(rows))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    files=[p.relative_to(R) for p in (R/'scripts').glob('*.py')]
    files += [p.relative_to(R) for p in (R/D).iterdir() if p.suffix in {'.md','.json'} and 'private' not in p.name.lower()]
    files += [p.relative_to(R) for p in (R/B/'configs').glob('*.json')]
    files += [p.relative_to(R) for p in (R/B/'validation').glob('*inputs*/**/*') if p.is_file()]
    rows=[packet(a.output,'traction-overlay',files)]
    if a.evidence:
        result=json.loads((R/D/'DELIVERY-RESULTS.json').read_text());files=[]
        for trial in result['trials']:
            root=R/trial['trial']
            files += [p.relative_to(R) for p in root.iterdir() if p.is_file() and p.suffix in {'.json','.npz','.yaml'}]
        files += [p.relative_to(R) for p in (R/B/'jobs').glob('*/*.json')]
        files += [p.relative_to(R) for p in (R/B/'jobs').glob('*/*.log')]
        files += [p.relative_to(R) for p in (R/B/'jobs').glob('*/source.patch')]
        files += [p.relative_to(R) for p in (R/B/'resources').glob('**/*') if p.is_file()]
        files += [D/'events.jsonl',D/'events-remote.jsonl']
        # Full 240 Hz actual normal contact records for the selected video.
        files += [p.relative_to(R) for p in (R/B/'selected-full-video-v13/simulation').glob('*.jsonl')]
        rows.append(packet(a.output,'traction-evidence',files))
    (a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
