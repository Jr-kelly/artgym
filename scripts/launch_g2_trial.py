"""Launch from a private immutable source copy; retain source and failure logs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from scripts.monitor_wuji_checkpoints import runtime_environment


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--module',default='scripts.run_g2_tabletop')
    p.add_argument('--python',default='/home/agiuser/miniconda3/envs/artgym/bin/python')
    p.add_argument('--source-root',type=Path,help='Freeze from an existing verified trial pin rather than the current workspace.')
    p.add_argument('--run-root',type=Path,help='Independent experiment directory; default preserves the original tabletop runs.')
    p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];run=a.run_root.resolve() if a.run_root else root/'runs/g2-tabletop-v1';pin=run/'source-pins'/a.name
    source_root=a.source_root.resolve() if a.source_root else root
    if a.source_root:
        source_manifest=json.loads((source_root/'SOURCE_SHA256.json').read_text())
        for name,sha in source_manifest.items():
            if hashlib.sha256((source_root/name).read_bytes()).hexdigest()!=sha:
                raise ValueError('Frozen source changed: '+name)
    pin.mkdir(parents=True,exist_ok=False)
    for folder in ['scripts','isaacgymenvs','assets','caches','rl_games']:
        shutil.copytree(source_root/folder,pin/folder,ignore=shutil.ignore_patterns('__pycache__','.git'),symlinks=False)
    py=str(Path(a.python).resolve())
    env=runtime_environment(dict(project=str(pin),python=py),0)
    env['VK_ICD_FILENAMES']='/etc/vulkan/icd.d/nvidia_icd.json'
    args=a.args[1:] if a.args and a.args[0]=='--' else a.args
    for flag in ['--teacher','--student','--grasp-plan','--seating-plan','--operation-pose','--table-regrasp-plan','--post-acquisition-pose']:
        if flag in args:
            i=args.index(flag)+1;source=Path(args[i]).resolve()
            if flag in ['--grasp-plan','--seating-plan','--operation-pose','--table-regrasp-plan','--post-acquisition-pose']:
                destination=pin/'inputs'/source.name;destination.parent.mkdir(exist_ok=True);shutil.copyfile(source,destination)
                args[i]=str(destination)
            else:args[i]=str(source)
    manifest={str(f.relative_to(pin)):hashlib.sha256(f.read_bytes()).hexdigest() for f in pin.rglob('*') if f.is_file()}
    (pin/'SOURCE_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    cmd=[py,'-m',a.module,'--output',str(run/a.name)]+args
    with (run/(a.name+'.log')).open('w') as log:
        child=subprocess.Popen(cmd,cwd=pin,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record=dict(started=datetime.now(timezone.utc).isoformat(),pid=child.pid,command=cmd,pin=str(pin),
        source_manifest_sha256=hashlib.sha256((pin/'SOURCE_SHA256.json').read_bytes()).hexdigest())
    (run/(a.name+'-process.json')).write_text(json.dumps(record,indent=2)+'\n')
    with (run/'events.jsonl').open('a') as f:f.write(json.dumps(dict(event='trial_launched',name=a.name,**record))+'\n')
    print(json.dumps(record))


if __name__=='__main__':main()
