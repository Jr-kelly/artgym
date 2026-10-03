"""Archive exacttracked Git source, excluding only irrelevant old evidence."""
import pathlib,subprocess,tarfile,hashlib,json
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';out=R/'runs/robust-knife-family-20261003/delivery/wuji-g2-source-final.tar.gz';assert not out.exists();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=R,text=True).strip();excluded_prefix='research/multigrasp-20260928/evidence/';entries=[];omitted=[]
record('final_exact_git_source_archive_started',config={'source_commit':commit,'source_tree':tree,'exclude_only':excluded_prefix},next='Archiveexacttracked bytes, excludeuntrackedprivatehuman/userFranka automatically')
class HashReader:
 def __init__(self,stream):self.stream=stream;self.hash=hashlib.sha256()
 def read(self,n=-1):
  data=self.stream.read(n);self.hash.update(data);return data
proc=subprocess.Popen(['git','archive','--format=tar',commit],cwd=R,stdout=subprocess.PIPE)
with tarfile.open(fileobj=proc.stdout,mode='r|') as incoming,tarfile.open(out,'w:gz',compresslevel=1) as target:
 for member in incoming:
  if member.name.startswith(excluded_prefix):omitted.append(member.name);continue
  if member.isdir():target.addfile(member);continue
  assert member.isfile(),(member.name,member.type)
  reader=HashReader(incoming.extractfile(member));target.addfile(member,reader);entries.append({'path':member.name,'bytes':member.size,'sha256':reader.hash.hexdigest()})
assert proc.wait()==0;assert entries
h=hashlib.sha256()
with out.open('rb') as stream:
 for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
m={'archive':out.name,'archive_bytes':out.stat().st_size,'archive_sha256':h.hexdigest(),'source_commit':commit,'source_tree':tree,'excluded_prefixes':[excluded_prefix],'omitted_paths':omitted,'files':entries,'scope':'ExacttrackedGit content exceptoldmultigrasp evidenceonly. Allcontroller/source/config/currentreport files retained, frozen1258 runtimefiles exact. SDKexternal; untrackedprivatehumanmedia/userFranka notincluded. Laterdeliveryclosure-onlycommit mayrecord audits ofthisarchive.'};mp=out.with_suffix(out.suffix+'.manifest.json');mp.write_text(json.dumps(m,indent=2));record('final_exact_git_source_archive_completed',evidence=str(mp.relative_to(R)),config={'source_commit':commit,'source_tree':tree,'files':len(entries),'omitted_paths':len(omitted)},archive_sha256=m['archive_sha256'],next='Uploadactualsourcearchive, downloadfresh andverify everydefaultrestore frozenfile beforephysicalexecution');print({k:v for k,v in m.items() if k not in ['files','omitted_paths']})
