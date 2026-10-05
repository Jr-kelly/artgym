"""Package the frozen runtime including every hashed recipe dependency."""
import argparse,json,subprocess,sys
from pathlib import Path
from scripts.package_wuji_traction import packet

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',action='store_true');a=p.parse_args()
    cmd=[sys.executable,'-m','scripts.package_wuji_newknife','--output',str(a.output)]
    if a.evidence:cmd.append('--evidence')
    subprocess.run(cmd,check=True)
    selection=json.loads(Path('research/newknife-20261005/FROZEN-CANDIDATE.json').read_text())
    manifest=json.loads((a.output/'newknife-overlay-files.json').read_text())
    files=[Path(r['path']) for r in manifest['files']]+[Path(s) for s in selection['required_sha256']]
    assert all('private' not in str(f).lower() and f.suffix.lower() not in {'.html','.jpg','.jpeg','.mp4'} for f in files)
    rows=json.loads((a.output/'packets.json').read_text());rows[0]=packet(a.output,'newknife-overlay',files)
    (a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))

if __name__=='__main__':main()
