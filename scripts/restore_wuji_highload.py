"""Restore highload evidence on immutable wrap and traction dependencies.

Requires a separately installed licensed Isaac Gym runtime. Executes simulation
only; no robot SDK/transport is loaded. Use a new empty destination.
"""
import argparse,json,os,subprocess,sys,tarfile
from pathlib import Path
from scripts.restore_wuji_traction import BASE,digest
TRACTION='720883ee29b204e7e8d5cdc023191f451fd6118f3347f3b745b5420a630c1e67'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-dir',type=Path,required=True);p.add_argument('--traction-overlay',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
 dest=a.destination.resolve();assert not dest.exists();packets=[]
 for name,sha in BASE.items():
  f=a.baseline_dir/name;assert digest(f)==sha,(name,'SHA mismatch');packets.append(f)
 assert digest(a.traction_overlay)==TRACTION;packets += [a.traction_overlay,a.overlay];dest.mkdir(parents=True)
 for packet in packets:
  with tarfile.open(packet) as tar:
   for m in tar.getmembers():assert dest in (dest/m.name).resolve().parents and not m.issym() and not m.islnk(),m.name
   tar.extractall(dest)
 manifest=json.loads((dest/'recovery-manifests/highload-overlay-files.json').read_text())
 for row in manifest['files']:assert digest(dest/row['path'])==row['sha256'],row['path']
 result=dict(packets=[dict(archive=f.name,sha256=digest(f)) for f in packets],verified_files=len(manifest['files']),real_robot_ran=False)
 if a.run:
  env=os.environ.copy();env['PYTHONPATH']=str(dest)+':'+str(dest/'rl_games');cmd=[sys.executable,'-m','scripts.run_wuji_highload_selected','--mode','capacity','--no-video','--output','runs/highload-restored']
  with (dest/'restore-run.log').open('w') as log:code=subprocess.call(cmd,cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
  result.update(exit_code=code,command=cmd)
  f=dest/'runs/highload-restored/simulation/functional-evaluation.json'
  if f.exists():result['evaluation']=json.loads(f.read_text())
 (dest/'RESTORE-RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if a.run:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
