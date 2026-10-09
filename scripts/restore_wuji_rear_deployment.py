"""Compose verified existing base + one current overlay into a NEW deployment root.
Never modifies base or distributes licensed Isaac Gym. stdlib-only, no prior overlay order.
"""
import argparse,hashlib,json,shutil,tarfile,tempfile
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def restore(base,overlay,dest,bundle_path='research/rear-sim2real-20261009/bundle-deploy-v8.json'):
    base=Path(base).resolve();dest=Path(dest).absolute()
    if dest.exists():raise FileExistsError('Deployment destination must be new: '+str(dest))
    if not (base/'isaacgymenvs').is_dir():raise ValueError('Use existing verified contact-transfer/ArtGym base root')
    with tempfile.TemporaryDirectory(prefix='wuji-rear-overlay-') as tmp:
        tmp=Path(tmp)
        with tarfile.open(overlay,'r:gz') as t:
            for m in t.getmembers():
                if Path(m.name).is_absolute() or '..' in Path(m.name).parts or not (m.isfile() or m.isdir()):raise ValueError('Unsafe archive member: '+m.name)
            t.extractall(tmp)
        if Path(bundle_path).is_absolute() or '..' in Path(bundle_path).parts:raise ValueError('Unsafe bundle path')
        bundle=tmp/bundle_path;s=json.loads(bundle.read_text());sources={}
        for n,h in s['required_sha256'].items():
            if Path(n).is_absolute() or '..' in Path(n).parts:raise ValueError('Unsafe dependency path: '+n)
            p=tmp/n if (tmp/n).is_file() else base/n
            if not p.is_file() or sha(p)!=h:raise ValueError('Missing/changed base dependency: '+n)
            sources[n]=p
        dest.mkdir(parents=True)
        try:
            for n in ['scripts','isaacgymenvs','rl_games']:
                shutil.copytree(base/n,dest/n,ignore=shutil.ignore_patterns('__pycache__','.git','*.pyc','runs','logs'))
            for n,p in sources.items():
                d=dest/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
            for p in tmp.rglob('*'):
                if p.is_file():d=dest/p.relative_to(tmp);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
            verified=all(sha(dest/n)==h for n,h in s['required_sha256'].items())
            result=dict(format='wuji-rear-restoration-v1',base=str(base),root=str(dest),overlay_sha256=sha(overlay),bundle_sha256=sha(dest/bundle.relative_to(tmp)),dependencies=len(sources),all_dependencies_sha256_match=verified,weights_reused=True,licensed_dependencies_copied=False,inference_run=False,real_robot_ran=False)
            (dest/'RESTORE-RECEIPT.json').write_text(json.dumps(result,indent=2));return result
        except Exception:
            # Preserve failure directory for inspection; never delete an existing workspace.
            (dest/'RESTORE-FAILED.txt').write_text('See raised exception. This new root is incomplete.\n');raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--bundle-path',default='research/rear-sim2real-20261009/bundle-deploy-v8.json');a=p.parse_args();print(json.dumps(restore(a.base,a.overlay,a.destination,a.bundle_path),indent=2))
if __name__=='__main__':main()
