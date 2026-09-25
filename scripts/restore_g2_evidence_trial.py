"""Restore one release trial's pinned source and print its exact launch command.

Preparation only: does not run physics, train, or restore a simulation state.
The destination is a new detached worktree; existing results are never changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--trial',required=True)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--python',required=True)
    p.add_argument('--teacher',type=Path,required=True)
    p.add_argument('--student',type=Path)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    src=a.evidence.resolve()/'trials'/a.trial
    overrides=json.loads((src/'source-overrides.json').read_text())
    dest=a.destination.resolve()
    if dest.exists():raise ValueError('Destination already exists; choose a new path.')
    subprocess.run(['git','worktree','add','--detach',str(dest),overrides['base_commit']],cwd=root,check=True)
    for name,sha in overrides['overrides'].items():
        target=dest/name
        if dest not in target.resolve().parents:
            raise ValueError('Invalid evidence path')
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(a.evidence/'sources'/'blobs'/sha,target)
    manifest=json.loads((src/'SOURCE_SHA256.json').read_text())
    for name,sha in manifest.items():
        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=sha:
            raise ValueError('Restored source differs: '+name)
    info=json.loads((src/(a.trial+'-process.json')).read_text())
    cmd=[a.python]+[v.replace(info['pin'],str(dest)) for v in info['command'][1:]]
    cmd[cmd.index('--output')+1]=str(dest/'reproduced-result')
    for flag,value in [('--teacher',a.teacher),('--student',a.student)]:
        if value is None:continue
        if flag in cmd:cmd[cmd.index(flag)+1]=str(value.resolve())
        else:cmd.extend([flag,str(value.resolve())])
    if '--group' in cmd and cmd[cmd.index('--group')+1]=='C' and a.student is None:
        raise ValueError('Group C needs --student.')
    script='#!/usr/bin/env bash\nset -eu\ncd '+shlex.quote(str(dest))+'\n'
    script+='export LD_LIBRARY_PATH='+shlex.quote(str(Path(a.python).resolve().parent.parent/'lib'))+':${LD_LIBRARY_PATH:-}\n'
    script+='export VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_icd.json\n'
    script+='export PYTHONPATH='+shlex.quote(str(dest)+':'+str(dest/'rl_games'))+'\n'
    script+='export PYTHONUNBUFFERED=1 PYTHONNOUSERSITE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MAX_JOBS=2 CUDA_VISIBLE_DEVICES=0\n'
    script+='unset RANK LOCAL_RANK WORLD_SIZE LOCAL_WORLD_SIZE MASTER_ADDR MASTER_PORT\n'
    script+=shlex.join(cmd)+'\n'
    (dest/'reproduce.sh').write_text(script)
    print(json.dumps(dict(verified_source_files=len(manifest),launch='bash '+shlex.quote(str(dest/'reproduce.sh')))))


if __name__=='__main__':main()
