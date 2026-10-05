"""Restore a newknife overlay on the two immutable wrap dependencies.
A separately installed licensed Isaac Gym runtime is required. Simulation only.
"""
import argparse,json,os,subprocess,sys,tarfile
from pathlib import Path
from scripts.restore_wuji_traction import BASE,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline-dir',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();dest=a.destination.resolve();assert not dest.exists();packets=[]
 for name,sha in BASE.items():
  f=a.baseline_dir/name;assert digest(f)==sha,(name,'SHA mismatch');packets.append(f)
 packets.append(a.overlay);dest.mkdir(parents=True)
 for f in packets:
  with tarfile.open(f) as tar:
   for m in tar.getmembers():assert dest in (dest/m.name).resolve().parents and m.isfile(),m.name
   tar.extractall(dest)
 manifest=json.loads((dest/'recovery-manifests/newknife-overlay-files.json').read_text())
 for row in manifest['files']:assert digest(dest/row['path'])==row['sha256'],row['path']
 result=dict(packets=[dict(name=f.name,sha256=digest(f)) for f in packets],verified_files=len(manifest['files']),real_robot_ran=False,scope=__doc__)
 if a.run:
  env=os.environ.copy();env['PYTHONPATH']=str(dest)+':'+str(dest/'rl_games');cmd=[sys.executable,'-m','scripts.run_wuji_newknife_selected','--no-video','--output','runs/newknife-restored']
  with (dest/'restore-run.log').open('w') as log:code=subprocess.call(cmd,cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
  result.update(command=cmd,exit_code=code);evaluation=dest/'runs/newknife-restored/simulation/newknife-evaluation.json'
  if evaluation.exists():result['evaluation']=json.loads(evaluation.read_text())
 (dest/'RESTORE-RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if a.run:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
