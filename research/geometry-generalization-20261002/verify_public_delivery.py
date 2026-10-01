"""Anonymous public download checks; uses the existing archive/checkpoint restorers."""
import datetime,hashlib,json,subprocess,urllib.request
from pathlib import Path
from scripts.record_wuji_geometry_goal import R,D,record
TAG='wuji-geometry-generalization-20261002-v1'
def request(url):
 return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Wuji-geometry-public-verification'}),timeout=120)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 dest=Path('/tmp/wuji-geometry-public-downloads-20261002');assert not dest.exists();dest.mkdir()
 with request('https://api.github.com/repos/Jr-kelly/artgym/releases/tags/'+TAG) as response:release=json.load(response)
 assert not release['draft'] and release['id']==401374769
 assets=[];page=1
 while True:
  with request('https://api.github.com/repos/Jr-kelly/artgym/releases/401374769/assets?per_page=100&page='+str(page)) as response:batch=json.load(response)
  assets+=batch
  if len(batch)<100:break
  page+=1
 actual={x['name']:x for x in assets};assert len(actual)==len(assets)
 expected={}
 for p in D.glob('upload-*.json'):
  x=json.loads(p.read_text())
  if isinstance(x,list):
   for item in x:
    if 'asset_id' in item:
     assert item['name'] not in expected or expected[item['name']]['sha256']==item['sha256'];expected[item['name']]=item
 assert expected.keys()==actual.keys(),(expected.keys()-actual.keys(),actual.keys()-expected.keys())
 for name,item in expected.items():assert actual[name]['state']=='uploaded' and actual[name]['digest']=='sha256:'+item['sha256']
 names=['geometry-frozen-parent-models.tar.gz','geometry-controlled-assets-v1.tar.gz','geometry-final-L80.tar.gz']+[name for name in actual if name.endswith('.mp4')];downloads=[]
 record('anonymous_public_key_artifact_download_started',release=release['html_url'],names=names,next='Verify anonymous bytes, use existing restore/checkpoint tools, decode all downloaded video frames')
 for name in names:
  target=dest/name
  with request(actual[name]['browser_download_url']) as response,target.open('xb') as f:
   for chunk in iter(lambda:response.read(8*1024*1024),b''):f.write(chunk)
  assert target.stat().st_size==actual[name]['size'] and sha(target)==expected[name]['sha256'];downloads.append(dict(name=name,url=actual[name]['browser_download_url'],sha256=sha(target),authentication='none'));print(json.dumps(downloads[-1]),flush=True)
 restored=dest/'restored';receipts=[]
 for name in names[:3]:
  out=subprocess.check_output(['python3','-m','scripts.restore_wuji_unified',str(dest/name),'--output',str(restored)],cwd=R,text=True);receipts.append(json.loads(out))
 models=json.loads((D/'final-freeze.json').read_text())['models']
 for path,digest in models.items():assert sha(restored/path)==digest
 import imageio.v2 as imageio
 videos=[]
 for name in names[3:]:
  spec=json.loads((D/'videos'/Path(name).with_suffix('.json').name).read_text());reader=imageio.get_reader(dest/name);meta=reader.get_meta_data();count=0
  try:
   for frame in reader:assert frame.ndim==3 and frame.shape[2]==3;count+=1
  finally:reader.close()
  assert count==spec['frames'];videos.append(dict(name=name,frames=count,duration_s=count/meta['fps'],decoded_all_frames=True))
 result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),release=release['html_url'],release_id=release['id'],tag=TAG,target_commitish=release['target_commitish'],published=True,all_asset_server_sha256_matches=True,asset_count=len(actual),assets=[dict(name=n,sha256=expected[n]['sha256'],size=actual[n]['size'],url=actual[n]['browser_download_url']) for n in actual],anonymous_downloads=downloads,restores=receipts,model_hashes=models,videos=videos,restore_root=str(restored),scope='Published bytes verified without authentication. CPU Adam/RNG audit and actual public-code GPU command smoke are separate final verification receipts.')
 (D/'public-verification.json').write_text(json.dumps(result,indent=2)+'\n');record('anonymous_public_key_download_restore_video_checks_passed',evidence='research/geometry-generalization-20261002/public-verification.json',asset_count=len(actual),next='Audit downloaded parent optimizer/RNG with existing tool; verify actual final public-code commands, then stop own monitor')
if __name__=='__main__':main()
