"""Launch local runs from one immutable source copy per code version.

Only Python scripts/configs are copied. Existing immutable assets/dependencies
are shared by symlink. Does not stop unrelated processes or launch remotely.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--module', choices=['scripts.run_g2_local','scripts.train_g2_local','scripts.run_g2_tabletop'], required=True)
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    base = ROOT/'runs/g2-local-policy-20260928'
    extra = args.args[1:] if args.args[:1] == ['--'] else args.args
    def option(command, flag, default=None):
        return command[command.index(flag)+1] if flag in command else default
    if args.module == 'scripts.train_g2_local':
        state = json.loads((base/'state.json').read_text())
        now = datetime.datetime.now(datetime.timezone.utc)
        delivery = datetime.datetime.fromisoformat(state['delivery_start_utc'])
        hours = float(option(extra, '--hours', 2.))
        accounted = float(state['budgets'].get('environment_debug_gpu_hours_charged',0.))
        for old in base.glob('*-launch.json'):
            item = json.loads(old.read_text())
            if item['module'] != 'scripts.train_g2_local':
                continue
            oldcmd = item['command']
            status = Path(option(oldcmd,'--output'))/'status.json'
            if status.exists():
                accounted += json.loads(status.read_text())['seconds']/3600
            else:
                # Reserve the entire declared limit for a running/uncertain job.
                accounted += float(option(oldcmd,'--hours',2.))
        if hours <= 0 or accounted+hours > state['budgets']['gpu_hours_max']:
            raise ValueError('Cumulative local learning budget exceeded: used/reserved %.4fh + requested %.4fh' % (accounted,hours))
        if now >= delivery or now+datetime.timedelta(hours=hours) > delivery:
            raise ValueError('Training would enter the reserved delivery window; shorten hours')
    files = sorted((ROOT/'scripts').glob('*.py')) + sorted((ROOT/'configs/g2_local').rglob('*'))
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    version = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    pin = base/'source-pins'/version
    if not pin.exists():
        pin.mkdir(parents=True)
        for name in ['scripts','configs']:
            shutil.copytree(ROOT/name,pin/name)
        for name in ['isaacgymenvs','rl_games','assets','caches']:
            (pin/name).symlink_to(ROOT/name, target_is_directory=True)
        (pin/'runs').symlink_to(ROOT/'runs', target_is_directory=True)
        (pin/'source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    manifest = base/(args.name+'-launch.json')
    if manifest.exists():
        raise FileExistsError('Never overwrite a launch manifest: '+str(manifest))
    cmd = ['/home/agiuser/miniconda3/envs/artgym/bin/python','-u','-m',args.module]+extra
    env = os.environ.copy()
    env.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:'+env['PATH'],
        LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',
        PYTHONPATH=str(pin)+':'+str(pin/'rl_games'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    log = base/(args.name+'.log')
    with log.open('x') as stream:
        child = subprocess.Popen(cmd,cwd=pin,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    info = dict(pid=child.pid, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=cmd,cwd=str(pin),source_version=version,log=str(log),
        module=args.module,scope='local machine only',stop='SIGTERM this PID only; trainer checkpoints and exits')
    manifest.write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2))


if __name__=='__main__':
    main()
