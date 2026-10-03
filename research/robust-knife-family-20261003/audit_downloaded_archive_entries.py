"""Stream-verify every currently downloaded closed archive entry against manifest."""
import pathlib,tarfile,json,hashlib,datetime
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';root=pathlib.Path('/tmp/wuji-release-download-verification-20261003');results=[]
record('downloaded_closed_archives_full_entry_audit_started',config={'directory':str(root)},next='Check everyactualdownloadedfile member, not justarchiveSHA')
for p in sorted(root.glob('*.tar.gz')):
 mp=p.with_suffix(p.suffix+'.manifest.json');assert mp.is_file(),mp;m=json.loads(mp.read_text());m=json.loads((root/(p.name+'.entries.manifest.json')).read_text()) if 'files' not in m else m;expected={x['path']:x for x in m['files']};seen=set();total=0
 with tarfile.open(p,'r:gz') as tar:
  for member in tar:
   assert not pathlib.Path(member.name).is_absolute() and '..' not in pathlib.Path(member.name).parts
   if member.isdir():continue
   assert member.isfile(),(p,member.name,member.linkname);assert member.name in expected and member.name not in seen,(p,member.name);item=expected[member.name];assert member.size==item['bytes'];stream=tar.extractfile(member);h=hashlib.sha256()
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
   assert h.hexdigest()==item['sha256'],(p,member.name);seen.add(member.name);total+=member.size
 assert seen==set(expected),(p,set(expected)-seen);results.append({'archive':p.name,'verified_file_members':len(seen),'uncompressed_file_bytes':total,'archive_sha256':m['archive_sha256']});print(json.dumps(results[-1]),flush=True)
j={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archives':results,'total_file_members':sum(r['verified_file_members'] for r in results),'scope':'Actualdownloadedclosed archive entries allSHA/size/path/type verified; finalsource/context archives assembledlater and audited separately. No extra physics/training or tasksuccess claims.'};out=D/'github-closed-downloaded-archives-full-entry-audit.json';out.write_text(json.dumps(j,indent=2));record('downloaded_closed_archives_full_entry_audit_completed',evidence=str(out.relative_to(R)),config={'archives':len(results),'file_members':j['total_file_members']},next='Finishfinitecontextpair and finalsource/defaultrestore checks');print({'archives':len(results),'files':j['total_file_members']})
