"""Incremental G2 evidence bundle; deduplicate source overrides, retain failures.

The prior repository commit and frozen checkpoints are referenced, not uploaded
again. Running trials are listed as pending and omitted from this snapshot.
"""
import argparse,hashlib,json,shutil,subprocess,tarfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='1482edd56fec726da0f6dca74011506dfe9324ea'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-root',type=Path,default=ROOT/'runs/g2-tabletop-v1')
    p.add_argument('--report',type=Path,default=ROOT/'research/g2-tabletop-baseline-20260925.md')
    p.add_argument('--extra-report',type=Path,action='append',default=[])
    p.add_argument('--base',default=BASE);p.add_argument('--label',default='v1')
    p.add_argument('--exclude-manifest',type=Path,action='append',default=[]);p.add_argument('--video-trial',action='append',default=[])
    p.add_argument('--video-named',action='append',default=[],help='TRIAL=descriptive-filename.mp4; names should state the achieved scope.')
    p.add_argument('--closeup-named',action='append',default=[],help='TRIAL=descriptive-filename.mp4; synchronized closeup from the same execution.')
    a=p.parse_args()
    base=a.base;excluded=set()
    for previous in a.exclude_manifest:excluded.update(json.loads(previous.read_text())['trials'])
    a.output.mkdir(parents=True,exist_ok=False);run=a.run_root.resolve();stage=a.output/'evidence';stage.mkdir()
    base_files=set(subprocess.check_output(['git','ls-tree','-r','--name-only',base],cwd=ROOT,text=True).splitlines())
    changed=set(subprocess.check_output(['git','diff',base,'--name-only'],cwd=ROOT,text=True).splitlines());cache={};included=[];pending=[];preparation_failures=[]
    def base_hash(name):
        if name not in base_files:return None
        if name not in cache:
            value=(subprocess.check_output(['git','show',base+':'+name],cwd=ROOT) if name in changed else (ROOT/name).read_bytes())
            cache[name]=hashlib.sha256(value).hexdigest()
        return cache[name]
    for pin in sorted((run/'source-pins').iterdir()):
        if pin.name in excluded:continue
        process=run/(pin.name+'-process.json');info=json.loads(process.read_text()) if process.exists() else {}
        proc=Path('/proc',str(info.get('pid',-1)),'stat')
        alive=False
        if proc.exists():
            fields=proc.read_text().split(') ')[1].split()
            alive=fields[0]!='Z' and (info.get('process_start_ticks') is None or fields[19]==str(info['process_start_ticks']))
        if alive:pending.append(pin.name);continue
        if not (pin/'SOURCE_SHA256.json').exists():
            if process.exists():raise ValueError('Started trial lacks immutable source manifest: '+pin.name)
            dest=stage/'preparation-failures'/pin.name;dest.mkdir(parents=True)
            if (pin/'inputs').exists():shutil.copytree(pin/'inputs',dest/'inputs')
            (dest/'NOTE.json').write_text(json.dumps(dict(status='incomplete preparation before process launch',
                source_manifest_exists=False,physical_execution=False,
                note='Partial local source copy retained locally; no executed source pin claimed. Root diagnostic/setup-error records accompany this bundle.'),indent=2)+'\n')
            preparation_failures.append(pin.name);continue
        included.append(pin.name);dest=stage/'trials'/pin.name;dest.mkdir(parents=True)
        result=run/pin.name
        if result.exists():
            for file in result.rglob('*'):
                if not file.is_file() or file.suffix in ['.mp4','.png']:continue
                target=dest/file.relative_to(result);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        for file in [process,run/(pin.name+'.log')]:
            if file.exists():shutil.copyfile(file,dest/file.name)
        manifest=json.loads((pin/'SOURCE_SHA256.json').read_text());overrides={}
        for name,sha in manifest.items():
            if base_hash(name)==sha:continue
            file=pin/name
            if digest(file)!=sha:raise ValueError('Source pin changed: '+str(file))
            blob=stage/'sources/blobs'/sha;blob.parent.mkdir(parents=True,exist_ok=True)
            if not blob.exists():shutil.copyfile(file,blob)
            overrides[name]=sha
        (dest/'source-overrides.json').write_text(json.dumps(dict(base_commit=base,overrides=overrides),indent=2)+'\n')
        shutil.copyfile(pin/'SOURCE_SHA256.json',dest/'SOURCE_SHA256.json')
    diagnostics=stage/'diagnostics';diagnostics.mkdir()
    for file in run.iterdir():
        if file.is_file() and file.suffix in ['.json','.jsonl','.py','.log','.txt','.csv','.yaml','.yml','.npz'] and not file.name.endswith('-process.json'):
            if file.suffix=='.log' and (run/(file.stem+'-process.json')).exists():continue
            shutil.copyfile(file,diagnostics/file.name)
    for file in [ROOT/'G2_TABLETOP_HANDOFF.md',a.report]+a.extra_report:
        shutil.copyfile(file,stage/file.name)
    manifest=dict(created=datetime.now(timezone.utc).isoformat(),base_commit=base,excluded_previous_trials=sorted(excluded),
        current_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        trials=included,pending_trials=pending,preparation_failures=preparation_failures,models='Reuse wuji-core-teacher-student-20260924-{teacher,student}.pth from release wuji-experiments-20260923',
        source_reconstruction='Checkout base_commit in a new directory, then overlay each path in source-overrides.json from sources/blobs/SHA256; verify SOURCE_SHA256.json.')
    (stage/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=a.output/('g2-wuji-tabletop-evidence-'+a.label+'.tar.gz')
    with tarfile.open(archive,'w:gz') as stream:stream.add(stage,arcname='g2-wuji-tabletop-evidence')
    videos={
        'A-g2-initialized-v4':'g2-wuji-A-preset-teacher-20s-success.mp4',
        'B-direct-grasp0-v5':'g2-wuji-B-direct-table-grasp-20s-failure.mp4',
        'B-pinch8-teacher-grasp0-v15':'g2-wuji-B-table-pickup-teacher-40s-failure.mp4',
        'C-pinch8-student-ideal-grasp0-v21':'g2-wuji-C-table-pickup-student-ideal-40s.mp4',
        'B-yaw90-contact-seat-grasp0-v17':'g2-wuji-B-contact-seating-28s-failure.mp4'}
    videos.update({name:'g2-wuji-'+name+'.mp4' for name in a.video_trial})
    for item in a.video_named:
        trial,name=item.split('=',1)
        if Path(name).name!=name or not name.endswith('.mp4'):raise ValueError('Expected a plain .mp4 filename')
        videos[trial]=name
    for trial,name in videos.items():
        src=run/trial/'continuous.mp4'
        if src.exists() and trial in included:shutil.copyfile(src,a.output/name)
    for item in a.closeup_named:
        trial,name=item.split('=',1)
        if Path(name).name!=name or not name.endswith('.mp4'):raise ValueError('Expected plain closeup .mp4 filename')
        src=run/trial/'hand-closeup.mp4'
        if not src.exists() or trial not in included:raise ValueError('Requested completed closeup absent: '+trial)
        if (a.output/name).exists():raise ValueError('Duplicate published video filename: '+name)
        shutil.copyfile(src,a.output/name)
    shutil.copyfile(a.report,a.output/'g2-wuji-tabletop-README.md')
    files=[f for f in a.output.iterdir() if f.is_file()]
    (a.output/'SHA256SUMS.txt').write_text(''.join(digest(f)+'  '+f.name+'\n' for f in sorted(files)))
    print(json.dumps(dict(output=str(a.output),included=len(included),pending=pending,archive_bytes=archive.stat().st_size)))


if __name__=='__main__':main()
