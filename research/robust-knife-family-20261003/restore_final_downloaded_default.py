"""Restore actual downloaded defaultpayload locally/remotely, audit frozenidentity."""
import argparse,pathlib,json,hashlib,subprocess,shlex,datetime,os
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';p=argparse.ArgumentParser();p.add_argument('--remote',action='store_true');a=p.parse_args();download=pathlib.Path('/tmp/wuji-release-download-verification-20261003');names=['wuji-g2-source-final.tar.gz','models-and-recovery-final.tar.gz','under-family-v1-assets-caches.tar.gz','height-sensitivity-assets-v1.tar.gz','fresh-validation-assets-v1.tar.gz'];items=[]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for c in iter(lambda:stream.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
for name in names:
 q=download/name;mp=download/(name+'.manifest.json');m=json.loads(mp.read_text());expected=m.get('archive_sha256',m.get('sha256'));assert sha(q)==expected;items.append({'name':name,'bytes':q.stat().st_size,'sha256':expected,'kind':'tar.gz','restore_default':True})
manifest=R/'runs/robust-knife-family-20261003/delivery/default-restore-only-manifest.json';manifest.write_text(json.dumps({'artifacts':items,'scope':'Temporarydefault5 restoremanifest foractualdownloadedbytes, finalReleaseflatmanifest delivered separately'},indent=2));destination='/tmp/wuji-final-release-restore-'+('remote' if a.remote else 'local')+'-20261003';hostartifacts='/tmp/wuji-final-download-artifacts-20261003' if a.remote else str(download);ssh=['ssh','-o','BatchMode=yes','-p','33024','wangjiarui@10.13.160.5'];env=os.environ.copy();env['PYTHONUTF8']='1';record('final_downloaded_default_empty_restore_started',config={'remote':a.remote,'destination':destination,'archives':items},next='Verifyfive actualdownloaded archives beforeempty extraction; frozenruntime/weights/inputs mustmatchexact')
if a.remote:
 files=[download/name for name in names]+[manifest,download/'restore_wuji_robust_delivery.py'];subprocess.run(['ssh','-o','BatchMode=yes','-p','33024','wangjiarui@10.13.160.5','mkdir -p '+shlex.quote(hostartifacts)],check=True);subprocess.run(['rsync','-a','-e','ssh -o BatchMode=yes -p 33024',*[str(f) for f in files],'wangjiarui@10.13.160.5:'+hostartifacts+'/'],check=True)
else:
 import shutil
 shutil.copy2(manifest,download/manifest.name)
cmd=['python3',hostartifacts+'/restore_wuji_robust_delivery.py','--artifacts',hostartifacts,'--manifest',hostartifacts+'/'+manifest.name,'--destination',destination]
result=subprocess.run(ssh+[shlex.join(cmd)] if a.remote else cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);assert result.returncode==0,result.stderr
code="""import pathlib,json,hashlib,datetime
root=pathlib.Path(DEST);D=root/'research/robust-knife-family-20261003';freeze=json.loads((D/'freeze.json').read_text());files=freeze['released_runtime_files_sha256'];assert len(files)==1258
for path,h in files.items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h,path
for group in ['frozen_inputs_sha256','base_weights_sha256']:
 for path,h in freeze[group].items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h,path
checkpoint=freeze['policy']['checkpoint_path'];actual=hashlib.sha256((root/checkpoint).read_bytes()).hexdigest();assert actual==freeze['policy']['sha256']
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'destination':str(root),'released_runtime_files_verified':len(files),'primary_checkpoint_sha256':actual,'all_frozen_inputs_baseweights_verified':True,'restore_receipt':json.loads((root/'wuji-restore-receipt.json').read_text()),'scope':'Actualdownloadeddefault5 archives emptyrestore; allfrozen runtime/weights/inputs exact. No physicalexecution orhardware claim fromthisaudit.'}))
""".replace('DEST',repr(destination));verify=subprocess.check_output(ssh+['python3 -c '+shlex.quote(code)] if a.remote else ['python3','-c',code],env=env,text=True);j=json.loads(verify);out=D/('final-downloaded-remote-empty-restore-audit.json' if a.remote else 'final-downloaded-local-empty-restore-audit.json');out.write_text(json.dumps(j,indent=2));record('final_downloaded_default_empty_restore_verified',evidence=str(out.relative_to(R)),config={'remote':a.remote,'destination':destination,'frozen_files':1258,'primary_checkpoint_sha256':j['primary_checkpoint_sha256']},next='RunactualfullTABLEnative/offline locally andallsevenfixedvalidation commands remotely');print(json.dumps(j))
