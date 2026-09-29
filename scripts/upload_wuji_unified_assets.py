"""Upload immutable completed archives to this run's draft release; verify digest."""
import json,subprocess,time
from pathlib import Path
from scripts.package_wuji_unified_completed import event,R,D,Q
TAG='wuji-unified-policy-20260930-v1';REPO='Jr-kelly/artgym'
def gh(*args):return subprocess.check_output(['gh',*args],cwd=R,text=True,timeout=600)
def main():
 release=json.loads(gh('release','view',TAG,'--repo',REPO,'--json','databaseId,url,isDraft'));rid=release['databaseId'];assert release['isDraft']
 verified=[]
 for receipt in sorted(D.glob('wuji-unified-*.receipt.json')):
  item=json.loads(receipt.read_text());p=R/item['archive'];assert p.exists();name=p.name
  assets=json.loads(gh('api',f'repos/{REPO}/releases/{rid}/assets','--paginate'))
  found=[a for a in assets if a['name']==name]
  if not found:
   event('release_asset_upload_started',name=name,sha256=item['sha256'],release=TAG,next='Verify server SHA256; do not overwrite existing assets')
   gh('release','upload',TAG,str(p),'--repo',REPO)
   assets=json.loads(gh('api',f'repos/{REPO}/releases/{rid}/assets','--paginate'));found=[a for a in assets if a['name']==name]
  assert len(found)==1
  a=found[0];assert a['size']==item['size'] and a['digest']=='sha256:'+item['sha256'],a
  verified.append(dict(name=name,sha256=item['sha256'],bytes=item['size'],asset_id=a['id'],url=a['browser_download_url']))
  (Q/'receipts/draft-assets-verified.json').write_text(json.dumps(dict(release=TAG,release_id=rid,assets=verified),indent=2)+'\n')
  event('release_asset_server_digest_verified',name=name,sha256=item['sha256'],release=TAG,next='Retain draft until final report/video/checkpoint decisions and public download verification')
 print(json.dumps(dict(verified=len(verified),release_id=rid)))
if __name__=='__main__':main()
