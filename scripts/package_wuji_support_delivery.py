"""Portable current-round overlays and evidence; reuse old large dependencies."""
import argparse,hashlib,json,subprocess,tarfile
from pathlib import Path
from scripts.record_wuji_support_goal import R,D,record

B=R/'runs/support-pressure-20261003'

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--group',required=True,choices=['source','runtime','learning','movies','evidence']);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert (D/'freeze.json').exists(),'Freeze candidate before final packaging'
    files=[]
    if a.group=='source':
        base='feb2118176893b1acf025abc1c9ad6b7b8a2cdcc'
        names=subprocess.check_output(['git','diff','--name-only','-z',base,'HEAD'],cwd=R).split(b'\0')
        files=[R/n.decode() for n in names if n]
        assert all(f.is_file() for f in files),'Source overlay must explicitly handle deletions'
        files.extend(f for f in D.iterdir() if f.is_file() and f.suffix in ['.md','.json','.jsonl','.py'])
    elif a.group=='runtime':
        weight=B/'train/joint-noisier-continuation-v31/update_000750.pth'
        selected=R/json.loads((D/'freeze.json').read_text())['checkpoint']
        files.extend([weight,weight.with_suffix('.sha256'),selected,selected.with_suffix('.sha256')])
        for root in [R/'assets/objects/knife_wuji_support_train_20261003',R/'assets/objects/knife_wuji_support_independent_20261003']:
            files.extend(f for f in root.rglob('*') if f.is_file())
        for folder in B.iterdir():
            if folder.is_dir() and ('config' in folder.name or folder.name.startswith('offline-input')):
                files.extend(f for f in folder.rglob('*') if f.is_file() and f.suffix in ['.json','.npz'])
        files.extend(f for f in B.glob('independent-*/*') if f.is_file() and f.suffix in ['.json','.npz'])
    elif a.group=='learning':
        folders=[B/'train/joint-noisier-continuation-v31']
        for pattern in ['*-support-timescale-v94-recovery1','*-support-load-features-v107','*-preparation-credit-v116','*-support-coordinates-v128']:
            folders.extend((B/'train').glob(pattern))
        for folder in folders:
            weights=sorted(folder.glob('update_*.pth'));assert weights,folder
            files.extend([weights[-1],weights[-1].with_suffix('.sha256')])
            files.extend(f for f in folder.iterdir() if f.is_file() and f.suffix in ['.json','.jsonl','.yaml'])
        files.extend(f for f in (B/'jobs').rglob('*') if f.is_file() and f.name in ['identity.json','result.json'])
        for name in ['strong750-normal-coordinate-interface-v129.pth','strong750-support-period5-v96.pth']:
            clone=B/'checkpoints'/name
            if clone.exists():files.extend([clone,clone.with_suffix('.sha256')])
    elif a.group=='movies':
        for folder in (B/'demo').iterdir():
            if not (folder/'pressure-annotated.mp4').exists():continue
            files.extend(f for f in folder.iterdir() if f.is_file() and (f.suffix in ['.mp4','.jpg'] or f.name in ['report.json','physics.json','plan.json']))
        files.extend(f for f in (B/'figures').rglob('*') if f.is_file())
        files.extend(f for f in (B/'browsable-report-final').rglob('*') if f.is_file())
    else:
        for root in [B/'demo',B/'jobs',B/'resources']:
            files.extend(f for f in root.rglob('*') if f.is_file() and f.suffix in ['.npz','.json','.jsonl','.log'])
        for folder in B.iterdir():
            if folder.is_dir() and ('contract' in folder.name or 'replay' in folder.name or folder.name.startswith('independent-') or folder.name.startswith('restored-')):
                files.extend(f for f in folder.rglob('*') if f.is_file() and f.suffix in ['.npz','.json','.jsonl','.log'])
    files=sorted(set(files));assert files and all(f.is_file() for f in files)
    assert all(R in f.parents for f in files)
    a.output.parent.mkdir(parents=True,exist_ok=True);assert not a.output.exists()
    record('support_delivery_package_started',config={'group':a.group,'files':len(files)},evidence=str(a.output.relative_to(R)),next='Archive exact selected bytes; restore once and execute one representative startup')
    entries=[dict(path=str(f.relative_to(R)),bytes=f.stat().st_size,sha256=digest(f)) for f in files]
    with tarfile.open(a.output,'w:gz',compresslevel=1,dereference=True) as tar:
        for f in files:tar.add(f,arcname=str(f.relative_to(R)),recursive=False)
    receipt=dict(group=a.group,archive=a.output.name,bytes=a.output.stat().st_size,sha256=digest(a.output),files=entries,scope='Current-round exact files; source overlays oldFeb211 source archive. No oldencoder weights or private attachment media. Scientific role remains separate from archive membership.')
    manifest=a.output.with_suffix(a.output.suffix+'.manifest.json');manifest.write_text(json.dumps(receipt,indent=2))
    record('support_delivery_package_closed',config={'group':a.group,'files':len(files),'bytes':receipt['bytes']},evidence=str(manifest.relative_to(R)),sha256=receipt['sha256'],next='Representative restore/startup and authorized newRelease publication')
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))

if __name__=='__main__':main()
