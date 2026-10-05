"""Restore the traction overlay on the two immutable wrap-force dependencies.

Licensed Isaac Gym and a compatible Python/CUDA environment are prerequisites.
No robot SDK or transport is included. --run executes one continuous simulation.
"""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path

BASE={
 'wrap-runtime.tar.gz':'3641e30850d88a41a5db4c385ff06d50ca321bc1f47e6527cd23fdcbd1a43fab',
 'wrap-learning-state.tar.gz':'519d9dc52d7cb1091da79901268933e8ccabfa908425bd1b1ccdc98ec84039b4'}
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-dir',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    destination=a.destination.resolve();assert not destination.exists(),'Use a new empty destination'
    packets=[]
    for name,sha in BASE.items():
        path=a.baseline_dir/name;assert digest(path)==sha,(name,'baseline hash mismatch');packets.append(path)
    packets.append(a.overlay);destination.mkdir(parents=True)
    receipts=[]
    for path in packets:
        with tarfile.open(path) as tar:
            for member in tar.getmembers():
                resolved=(destination/member.name).resolve()
                assert destination in resolved.parents and not member.issym() and not member.islnk(),member.name
            tar.extractall(destination)
        receipts.append(dict(archive=path.name,sha256=digest(path)))
    manifest=json.loads((destination/'recovery-manifests/traction-overlay-files.json').read_text())
    for row in manifest['files']:
        assert digest(destination/row['path'])==row['sha256'],row['path']
    result=dict(destination=str(destination),packets=receipts,overlay_files_verified=len(manifest['files']),run_requested=a.run,real_robot_ran=False)
    if a.run:
        env=os.environ.copy();env['PYTHONPATH']=str(destination)+':'+str(destination/'rl_games')
        cmd=[sys.executable,'-m','scripts.run_wuji_traction_selected','--no-video','--output','runs/traction-restored-verification']
        with (destination/'restored-run.log').open('w') as log:
            code=subprocess.call(cmd,cwd=destination,env=env,stdout=log,stderr=subprocess.STDOUT)
        result.update(command=cmd,exit_code=code)
        evaluation=destination/'runs/traction-restored-verification/simulation/functional-evaluation.json'
        if evaluation.exists():result['evaluation']=json.loads(evaluation.read_text())
    (destination/'RESTORE-RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    if a.run:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
