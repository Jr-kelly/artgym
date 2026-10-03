import pathlib,json,subprocess,hashlib,datetime,sys,urllib.request
from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_robust_goal import record
R=pathlib.Path.cwd();D=R/'research/robust-knife-family-20261003';base=R/'runs/robust-knife-family-20261003/delivery';download=pathlib.Path('/tmp/wuji-release-download-verification-20261003');gh='/home/agiuser/.local/bin/gh';env=host_tool_environment();tag='wuji-g2-continuous-knife-robust-20261003-v1';rid=402332478
def api(path,payload=None):
 cmd=[gh,'api','repos/Jr-kelly/artgym/'+path]
 if payload is not None:cmd+=['--method','PATCH','--input','-']
 p=subprocess.run(cmd,input=None if payload is None else json.dumps(payload).encode(),capture_output=True,cwd='/tmp',env=env);assert p.returncode==0,p.stderr.decode();return json.loads(p.stdout)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
m=json.loads((download/'release-manifest.json').read_text());assert sha(download/'release-manifest.json')==sha(base/'release-manifest.json');assert sha(download/'SHA256SUMS')==sha(base/'SHA256SUMS');expected={x['name']:x for x in m['artifacts']}
for name in ['release-manifest.json','SHA256SUMS']:expected[name]={'name':name,'sha256':sha(base/name),'bytes':(base/name).stat().st_size}
sums={}
for line in (download/'SHA256SUMS').read_text().splitlines(): s,n=line.split('  ',1);sums[n]=s
assert set(sums)==set(expected)-{'SHA256SUMS'}
release=api(f'releases/{rid}');assert release['tag_name']==tag;assert set(x['name'] for x in release['assets'])==set(expected);assert len(expected)==48
for a in release['assets']:
 e=expected[a['name']];assert a['size']==e['bytes'];assert a.get('digest')=='sha256:'+e['sha256'];assert sha(download/a['name'])==e['sha256'];assert sha(base/a['name'])==e['sha256'];assert a['name']=='SHA256SUMS' or sums[a['name']]==e['sha256']
commit=m['current_github_delivery_commit'];local=m['current_local_delivery_git_commit'];tree=subprocess.check_output(['git','rev-parse',local+'^{tree}'],text=True).strip();assert api('git/commits/'+commit)['tree']['sha']==tree
resources=json.loads((D/'FINAL-RESOURCE-AUDIT.json').read_text());assert resources['minimum_12h_met'];assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(resources['utc'])).total_seconds()<900
pre={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'assets':len(expected),'all_server_and_actual_download_bytes_verified':True,'target_github_commit':commit,'target_local_commit':local,'target_exact_git_tree':tree,'draft':release['draft']};(D/'github-final-flat-payload-verification.json').write_text(json.dumps(pre,indent=2));record('final_flat_payload_all48_assets_verified',evidence=str((D/'github-final-flat-payload-verification.json').relative_to(R)),config=pre,next='Publish authorized new Release after actual minimumtime/resource/restore gates')
if '--publish' not in sys.argv: print(json.dumps(pre));sys.exit(0)
body=(base/'RELEASE-NOTES.md').read_text()
if release['draft']: release=api(f'releases/{rid}',{'draft':False,'target_commitish':commit,'body':body,'name':'G2 + Wuji v1: continuous table pickup, loaded slider operation and frozen generalization'})
assert not release['draft'];assert release['body']==body;assert release['target_commitish']==commit
ref=api('git/ref/tags/'+tag)['object'];tag_commit=api('git/tags/'+ref['sha'])['object']['sha'] if ref['type']=='tag' else ref['sha'];assert tag_commit==commit;assert api('git/commits/'+tag_commit)['tree']['sha']==tree;assert len(release['assets'])==48
url='https://github.com/Jr-kelly/artgym/releases/download/'+tag+'/release-manifest.json'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Wuji-delivery-verification'}),timeout=60) as response: public_manifest=response.read(); public_url=response.geturl()
assert hashlib.sha256(public_manifest).hexdigest()==expected['release-manifest.json']['sha256']
receipt=dict(pre,anonymous_public_manifest_sha256=hashlib.sha256(public_manifest).hexdigest(),anonymous_public_download_verified=True,published_at=release['published_at'],draft=False,release_url=release['html_url'],tag_commit=tag_commit,tag_tree=tree,no_real_robot_actions=True);(D/'github-final-release-publication-verification.json').write_text(json.dumps(receipt,indent=2));record('new_github_release_publication_verified',evidence=str((D/'github-final-release-publication-verification.json').relative_to(R)),config=receipt,phase='Published new Release; final handoff closure',next='Persist final publication receipts and capability limits in branch/handoff',state_updates={'release_published':True,'release_url':receipt['release_url'],'release_tag_commit':tag_commit});print(json.dumps(receipt))
