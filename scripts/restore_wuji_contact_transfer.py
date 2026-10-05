"""Overlay an already verified singlepush runtime; one optional1.25N replay.
Use the old release restore once for a first installation, then this small overlay.
"""
import argparse,hashlib,json,subprocess,sys,tarfile,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--verified-base-root',type=Path,required=True);p.add_argument('--overlay',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();dest=a.destination.resolve();assert not dest.exists();dest.mkdir(parents=True)
subprocess.run(['cp','-a','--reflink=auto',str(a.verified_base_root.resolve())+'/.',str(dest)],check=True)
with tarfile.open(a.overlay) as tar:
 for m in tar.getmembers():assert m.isfile() and dest in (dest/m.name).resolve().parents,m.name
 tar.extractall(dest)
m=json.loads((dest/'recovery-manifests/contact-transfer-overlay-files.json').read_text())
for r in m['files']:assert hashlib.sha256((dest/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
result=dict(overlay_sha256=hashlib.sha256(a.overlay.read_bytes()).hexdigest(),verified_overlay_files=len(m['files']),baseline_source=str(a.verified_base_root),baseline_is_previously_verified=True,real_robot_ran=False)
if a.run:
 cmd=[sys.executable,'-m','scripts.run_wuji_contact_transfer_selected','--no-video','--load','1.25','--output','runs/contact-transfer-restored-125']
 env=os.environ.copy();env['PYTHONPATH']=str(dest)+':'+str(dest/'rl_games');env['PYTHONNOUSERSITE']='1'
 with (dest/'contact-transfer-restore.log').open('w') as f:r=subprocess.run(cmd,cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT)
 result['exit_code']=r.returncode;ev=dest/'runs/contact-transfer-restored-125/simulation/extension-evaluation.json'
 if ev.exists():result['evaluation']=json.loads(ev.read_text())
(dest/'CONTACT-TRANSFER-RESTORE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if a.run:raise SystemExit(result['exit_code'])
