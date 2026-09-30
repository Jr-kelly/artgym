"""Incremental upload to this round's independent draft release, no overwrite."""
import json,subprocess
from scripts.record_wuji_recovery import record,R,D
TAG='wuji-artmanip-recovery-20260930-v1';REPO='Jr-kelly/artgym'
def gh(*args):return subprocess.check_output(['gh',*args],cwd=R,text=True,timeout=900)
def main():
    release=json.loads(gh('release','view',TAG,'--repo',REPO,'--json','databaseId,url,isDraft'));rid=release['databaseId'];assert release['isDraft']
    verified=[]
    assets=json.loads(gh('api',f'repos/{REPO}/releases/{rid}/assets','--paginate'))
    for receipt in sorted((R/'delivery/artmanip-recovery-20260930').glob('*.receipt.json')):
        item=json.loads(receipt.read_text());p=R/item['archive'];assert p.exists()
        assert item['size'] <= 2*1024**3, 'Split oversized archives before GitHub upload: '+str(p)
        found=[a for a in assets if a['name']==p.name]
        if not found:
            record('release_upload_started',name=p.name,sha256=item['sha256'],release=TAG,next='Verify server digest')
            gh('release','upload',TAG,str(p),'--repo',REPO)
            assets=json.loads(gh('api',f'repos/{REPO}/releases/{rid}/assets','--paginate'));found=[a for a in assets if a['name']==p.name]
        assert len(found)==1
        a=found[0];assert a['size']==item['size'] and a['digest']=='sha256:'+item['sha256']
        verified.append(dict(name=p.name,sha256=item['sha256'],bytes=item['size'],asset_id=a['id'],url=a['browser_download_url']))
        (D/'draft-assets-verified.json').write_text(json.dumps(dict(release=TAG,release_id=rid,assets=verified),indent=2)+'\n')
        record('release_asset_verified',name=p.name,sha256=item['sha256'],next='Continue experiment; final publication requires freeze and download verification')
    print(json.dumps(dict(verified=len(verified),release_id=rid)))
if __name__=='__main__':main()
