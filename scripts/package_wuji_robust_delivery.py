"""Package this round's actual models/evidence with portable paths and hashes."""
import argparse, hashlib, json, tarfile
from pathlib import Path
from scripts.record_wuji_robust_goal import R, D, record


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--group',choices=['weights','demos','development','estimator','receipts','validation'],required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); a.output=a.output.resolve(); base=R/'runs/robust-knife-family-20261003'; files=[]
    if a.group=='weights':
        files.extend([R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',base/'train/geometric-P1/update_000050.pth',base/'train/geometric-reference-P0/geometric_reference.pth'])
        for folder in (base/'train').iterdir():
            if not folder.is_dir() or not (folder/'complete.json').exists(): continue
            complete=json.loads((folder/'complete.json').read_text()); update=complete.get('update')
            if update is None: continue
            weight=folder/f'update_{update:06d}.pth'; assert weight.exists(), weight
            files.extend([weight,weight.with_suffix('.sha256')])
            files.extend(f for f in folder.iterdir() if f.suffix in ['.yaml','.json','.jsonl'])
        for name in ['head-temporal-capacity-v1','head-measured-capacity-v2','head-history-v1','head-measured-v2']:
            folder=base/'estimator'/name
            if folder.exists(): files.extend(f for f in folder.iterdir() if f.is_file() and f.name in ['best.pth','last.pth','report.json','args.json','learning.jsonl'])
        for name in ['history-P50-v1','support-P50-v1','temporal-support-P50-v1','pressure-P50-v1','middle-P50-v1','middle-P50-v5','middle-P0-v5']:
            folder=base/'train'/name
            if folder.exists(): files.extend(f for f in folder.iterdir() if f.is_file())
        for folder in (base/'train').glob('exploration-*-v1'):
            files.extend(f for f in folder.iterdir() if f.is_file())
        # Evaluated intermediate weights are distinct from final recovery
        # checkpoints; retain both so closed comparisons can be reproduced.
        for report in (base/'checks').glob('*/report.json'):
            checkpoint=json.loads(report.read_text()).get('args',{}).get('checkpoint')
            if checkpoint:
                weight=R/checkpoint;assert weight.is_file(),weight;files.append(weight)
                if weight.with_suffix('.sha256').exists():files.append(weight.with_suffix('.sha256'))
    elif a.group=='demos':
        endings=['v37','v38','v39','v45','v46','v50','v55','v56','v58','v59','v60','v61','v62','v63','v64']
        for folder in (base/'demo').iterdir():
            if folder.is_dir() and any(folder.name.endswith(e) for e in endings) and (folder/'report.json').exists(): files.extend(f for f in folder.iterdir() if f.is_file())
        folder=base/'checks/batch-video-full-v49';files.extend(f for f in folder.iterdir() if f.is_file())
        folder=base/'deploy/P50-offline-v1';files.extend(f for f in folder.iterdir() if f.is_file())
    elif a.group=='development':
        for folder in (base/'checks').iterdir():
            if not folder.is_dir() or not (folder/'report.json').exists() or folder.name.startswith('independent-'): continue
            files.extend(f for f in folder.iterdir() if f.is_file() and f.name in ['report.json','episodes.jsonl','initial-snapshot.npz','bridge-parity.json','parity-packets.npz'])
        for name in ['direct-G2-P50-mixed512-v28','P50-early512-v40','AI200-joint-v44','P50-lift8-joint512-v51']:
            files.append(base/'checks'/name/'trace.npz')
        for folder in (base/'checks').glob('joint-component-*'):
            if (folder/'report.json').exists():files.append(folder/'trace.npz')
    elif a.group=='estimator':
        for name in ['temporal-capacity-train-v1','temporal-capacity-fresh-v1','temporal-capacity-offline-v3']:
            folder=base/'estimator'/name;files.extend(f for f in folder.iterdir() if f.is_file())
    elif a.group=='receipts':
        for folder in (base/'jobs').iterdir():
            if (folder/'result.json').exists(): files.extend(f for f in folder.iterdir() if f.is_file())
    elif a.group=='validation':
        assert (D/'freeze.json').exists(), 'Freeze candidate before independent delivery'
        for folder in (base/'checks').glob('independent-*'):
            assert (folder/'report.json').exists(), folder
            files.extend(f for f in folder.iterdir() if f.is_file())
        assert files, 'Independent validation has not completed'
    files=sorted(set(files));assert files and all(f.is_file() for f in files)
    entries=[dict(path=str(f.relative_to(R)),bytes=f.stat().st_size,sha256=digest(f)) for f in files]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    record('delivery_package_started',config=dict(group=a.group,output=str(a.output),files=len(files)),next='Archive exact listed bytes, verify portable manifest and archive hash')
    with tarfile.open(a.output,'w:gz',compresslevel=1) as tar:
        for f in files: tar.add(f,arcname=str(f.relative_to(R)),recursive=False)
    receipt=dict(group=a.group,archive=a.output.name,archive_bytes=a.output.stat().st_size,archive_sha256=digest(a.output),files=entries,scope='Actual artifacts; scientific role determined by report/identity, not archive membership. No real robot actions or human attachment media.')
    manifest=a.output.with_suffix(a.output.suffix+'.manifest.json');manifest.write_text(json.dumps(receipt,indent=2))
    record('delivery_package_completed',evidence=str(manifest.relative_to(R)),config=dict(group=a.group,files=len(files)),archive_sha256=receipt['archive_sha256'],next='Restore and verify selected artifacts before final Release publication')
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))


if __name__=='__main__': main()
