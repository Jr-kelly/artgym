"""Audit actually downloaded report/checkpoint references across all final payload archives."""
import pathlib,json,tarfile,hashlib,collections
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';root=pathlib.Path('/tmp/wuji-release-download-verification-20261003');manifest=json.loads((root/'release-manifest.json').read_text());archives=[x for x in manifest['artifacts'] if x['kind']=='tar.gz'];available={};reports={};origins={};checkpoint_variants=collections.defaultdict(set)
record('final_downloaded_combined_model_reference_coverage_started',config={'archives':len(archives)},next='Read actual archived report bytes, verify every checkpoint reference has matching supplied bytes across main/context/recovery packages')
for item in archives:
 m=json.loads((root/(item['name']+'.manifest.json')).read_text());m=json.loads((root/(item['name']+'.entries.manifest.json')).read_text()) if 'files' not in m else m
 for entry in m['files']:
  if entry['path'].endswith('.pth'):checkpoint_variants[entry['path']].add(entry['sha256'])
  available[entry['path']]=entry['sha256']
 wanted={e['path']:e for e in m['files'] if e['path'].startswith('runs/robust-knife-family-20261003/') and e['path'].endswith('/report.json')}
 if not wanted:continue
 with tarfile.open(root/item['name'],'r:gz') as tar:
  for member in tar:
   if member.name not in wanted:continue
   data=tar.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==wanted[member.name]['sha256'];j=json.loads(data);reports[member.name]=j;origins[member.name]=item['name']
refs=[]
for path,j in reports.items():
 args=j.get('args',{});args=args if isinstance(args,dict) else {};checkpoint=args.get('checkpoint',j.get('residual_checkpoint'))
 if checkpoint:
  assert checkpoint in checkpoint_variants,(path,checkpoint)
  expected=j.get('checkpoint_sha256',j.get('weight_sha256',{}).get(checkpoint));assert expected in checkpoint_variants[checkpoint],(path,checkpoint,expected,checkpoint_variants[checkpoint]);refs.append({'report':path,'report_archive':origins[path],'checkpoint':checkpoint,'sha256':expected})
 for weight,expected in j.get('weight_sha256',{}).items():assert expected in checkpoint_variants[weight],(path,weight)
p=D/'final-downloaded-combined-model-reference-coverage.json';out={'reports':len(reports),'reports_with_verified_checkpoint_reference':len(refs),'supplied_checkpoint_paths':len(checkpoint_variants),'verified_references':refs,'scope':'Actual archived report bytes and manifest-backed supplied model hashes across all final archives. Trained serialization/loading and actual resume execution separately audited. Does not claim every historical source/debug file is an evaluated candidate or all optional development trajectories are public.'};p.write_text(json.dumps(out,indent=2));record('final_downloaded_combined_model_reference_coverage_verified',evidence=str(p.relative_to(R)),config={k:out[k] for k in ['reports','reports_with_verified_checkpoint_reference','supplied_checkpoint_paths']},next='Close final downloaded payload audit, publication and native goal');print({k:v for k,v in out.items() if k!='verified_references'})
