"""Finite execution verification of both actually downloaded final context Adam/RNG checkpoints."""
import pathlib,json,subprocess,os,concurrent.futures,shlex,hashlib
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';download=pathlib.Path('/tmp/wuji-release-download-verification-20261003');fresh='/tmp/wuji-final-release-restore-remote-20261003';artifacts='/tmp/wuji-final-download-artifacts-20261003';ssh=['ssh','-o','BatchMode=yes','-p','33024','wangjiarui@10.13.160.5'];archive='closing-context-adaptation-evidence.tar.gz';m=json.loads((download/(archive+'.manifest.json')).read_text());h=hashlib.sha256()
with (download/archive).open('rb') as f:
 for c in iter(lambda:f.read(1048576),b''):h.update(c)
assert h.hexdigest()==m['archive_sha256'];assert (D/'final-downloaded-remote-empty-restore-audit.json').is_file();plan=json.loads((D/'final-downloaded-context-resume-preregistration.json').read_text());assert plan['absolute_end_update']==384
record('final_downloaded_context_checkpoint_execution_recovery_started',evidence=str((D/'final-downloaded-context-resume-preregistration.json').relative_to(R)),config={'fresh_root':fresh,'archive_sha256':m['archive_sha256'],'new_updates_each':34},next='Verify actual downloaded archive entries, add only absent or byte-identical evidence files, resume both actual final350 optimizers to384 without candidate evaluation')
subprocess.check_call(['rsync','-a','-e','ssh -o BatchMode=yes -p 33024',str(download/archive),str(download/(archive+'.manifest.json')),'wangjiarui@10.13.160.5:'+artifacts+'/'])
code='''import pathlib,json,tarfile,hashlib
root=pathlib.Path(FRESH);p=pathlib.Path(ARTIFACTS)/ARCHIVE;m=json.loads(p.with_suffix(p.suffix+'.manifest.json').read_text());expected={x['path']:x for x in m['files']};seen=set()
assert hashlib.sha256(p.read_bytes()).hexdigest()==m['archive_sha256']
with tarfile.open(p,'r:gz') as tar:
 for entry in tar:
  assert entry.isfile() and not pathlib.Path(entry.name).is_absolute() and '..' not in pathlib.Path(entry.name).parts;assert entry.name in expected and entry.name not in seen
  data=tar.extractfile(entry).read();item=expected[entry.name];assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'];target=root/entry.name
  if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256'],entry.name
  else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  seen.add(entry.name)
assert seen==set(expected);print(json.dumps({'files':len(seen),'sha256':m['archive_sha256'],'existing_files_unchanged':True}))
'''.replace('FRESH',repr(fresh)).replace('ARTIFACTS',repr(artifacts)).replace('ARCHIVE',repr(archive));subprocess.check_call(ssh+['python3 -c '+shlex.quote(code)])
env=os.environ.copy();env['WUJI_WIDTH_SSH_ARGV']=json.dumps(ssh);py='/home/agiuser/miniconda3/envs/artgym/bin/python'
def run(row):
 label,gpu=row;old='closing-context-'+label+'-training-v1';identity=json.loads((R/'runs/robust-knife-family-20261003/jobs'/old/'result.json').read_text());cmd=list(identity['executed_command']);cmd[cmd.index('--updates')+1]='384';cmd[cmd.index('--resume')+1]='runs/robust-knife-family-20261003/train/closing-context-'+label+'-v1/update_000350.pth';output='runs/robust-knife-family-20261003/train/delivery-restored-context-'+label+'-v2';cmd[cmd.index('--output')+1]=output;name='release-recovery-context-'+label+'-resume-v2';shell='cd '+shlex.quote(fresh)+' && exec '+shlex.join(cmd);args=[py,'-m','scripts.wuji_robust_jobs','--gpu',str(gpu),'--seconds','1800','--remote-root','/tmp/artgym-robust-20261003',name,'--','bash','-c',shell];assert subprocess.call(args,env=env,cwd=R)==0;subprocess.check_call(['rsync','-az','-e','ssh -o BatchMode=yes -p 33024','wangjiarui@10.13.160.5:'+fresh+'/'+output+'/',str(R/output)+'/']);complete=json.loads((R/output/'complete.json').read_text());assert complete['update']==384 and complete['transitions']==2228224;return {'name':name,'gpu':gpu,'output':output,'complete':complete,'input_checkpoint':cmd[cmd.index('--resume')+1]}
with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(run,[('AT',0),('AU',2)]))
p=D/'final-downloaded-context-resume-execution.json';p.write_text(json.dumps({'results':results,'scope':'Finite actual downloaded Adam/RNG checkpoint execution test; 34newupdates each gives1088 controlframes, beyond full36s firstepisode. No new candidate validation/promotion or primary score.'},indent=2));record('final_downloaded_context_checkpoint_execution_recovery_completed',evidence=str(p.relative_to(R)),conclusion='Both actual downloaded final350 models resumed Adam/RNG to384, ran scripted/active phases and new physical episode boundaries normally',next='Include recovered weights/Adam/RNG/logs/receipts with final recovery evidence; no new score or candidate selection');print(json.dumps(results))
