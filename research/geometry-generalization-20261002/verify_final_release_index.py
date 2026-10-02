"""Final index via existing gh metadata access; artifact download remains anonymous."""
import json,hashlib,urllib.request,datetime,subprocess
from pathlib import Path
from scripts.record_wuji_geometry_goal import D,R,record
from scripts.host_tool_environment import host_tool_environment
name='geometry-public-verification-evidence.tar.gz';expected={}
for p in D.glob('upload-*.json'):
 x=json.loads(p.read_text())
 if isinstance(x,list):
  for item in x:
   if 'asset_id' in item:expected[item['name']]=item
assets=json.loads(subprocess.check_output(['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/releases/401374769/assets?per_page=100'],env=host_tool_environment(),text=True));actual={x['name']:x for x in assets};assert len(actual)==40 and actual.keys()==expected.keys()
for n,e in expected.items():assert actual[n]['digest']=='sha256:'+e['sha256'] and actual[n]['state']=='uploaded'
target=Path('/tmp/wuji-geometry-public-downloads-20261002')/name;h=hashlib.sha256()
with urllib.request.urlopen(urllib.request.Request(actual[name]['browser_download_url'],headers={'User-Agent':'Wuji-geometry-final-index'}),timeout=120) as response,target.open('xb') as f:
 for chunk in iter(lambda:response.read(8*1024*1024),b''):h.update(chunk);f.write(chunk)
assert h.hexdigest()==expected[name]['sha256'];restored=Path('/tmp/wuji-geometry-public-verification-packet-restore-20261002');receipt=json.loads(subprocess.check_output(['python3','-m','scripts.restore_wuji_unified',str(target),'--output',str(restored)],cwd=R,text=True))
index=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),release_id=401374769,release='https://github.com/Jr-kelly/artgym/releases/tag/wuji-geometry-generalization-20261002-v1',asset_count=len(actual),all_sha256_verified=True,metadata_access='Authenticated existingghAPI after publicAPI403rate-limit; artifactdownload remains anonymous',assets=[dict(name=n,size=actual[n]['size'],sha256=expected[n]['sha256'],url=actual[n]['browser_download_url']) for n in actual],administrative_packet_anonymous_download=dict(name=name,url=actual[name]['browser_download_url'],sha256=h.hexdigest(),authentication='none',restore=receipt),note='39core scientificassets +1post-publication verification packet; no newcapability samples or sciencechanges afterfinal freeze.')
(D/'final-release-index.json').write_text(json.dumps(index,indent=2)+'\n');p=json.loads((D/'public-verification.json').read_text());(D/'public-key-checks-before-administrative-packet.json').write_text(json.dumps(p,indent=2)+'\n');p['asset_count']=40;p['assets']=index['assets'];p['final_index_utc']=index['checked_utc'];p['administrative_packet']=index['administrative_packet_anonymous_download'];p['final_index_metadata_access']=index['metadata_access'];(D/'public-verification.json').write_text(json.dumps(p,indent=2)+'\n')
s=json.loads((D/'STATE.json').read_text());delivery=s['delivery'];delivery.update(assets=40,public_verified=True);record('complete40_asset_public_index_and_verification_packet_restore_passed',evidence='research/geometry-generalization-20261002/final-release-index.json',state_updates={'delivery':delivery,'public_release_verified':True},next='Commit/push closure records, verify remote branch and tag; nativeGoalcomplete only after finalGitdelivery')
print('All40 serverdigests verified; verificationpacket anonymous restore',receipt['restored_files'])
