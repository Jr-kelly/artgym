"""Publish the prepared, authorized newknife failure-evidence release."""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
from scripts.publish_wuji_wrap_snapshot import api
from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_newknife_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--resume-id',type=int);a=p.parse_args()
    d=Path('research/newknife-20261005');state=json.loads((d/'STATE.json').read_text());target=state['github_commit'];manifest=json.loads((a.stage/'RELEASE-ARTIFACTS.json').read_text())
    tag='wuji-g2-newknife-20261005-v1';body=(d/'RELEASE-NOTES.md').read_text()
    if a.resume_id:
        release=api('releases/'+str(a.resume_id));assert release['draft'] and release['tag_name']==tag and release['target_commitish']==target
    else:
        release=api('releases',dict(tag_name=tag,target_commitish=target,name='G2 + Wuji new knife: calibrated asset and continuous failure evidence',body=body,draft=True,prerelease=True))
        (d/'RELEASE-DRAFT.json').write_text(json.dumps(release,indent=2))
        record('prepared_release_draft_created',str(d/'RELEASE-DRAFT.json'),config={'release_id':release['id'],'target':target},next_step='Upload each prepared artifact and verify server digests before publication')
        subprocess.run([__import__('sys').executable,'-m','scripts.upload_wuji_release_assets','--release-id',str(release['id']),'--verification',str(d/'RELEASE-UPLOAD-VERIFIED.json')]+[str(a.stage/r['name']) for r in manifest['assets']],check=True)
    uploaded=api('releases/'+str(release['id']));assets={r['name']:r for r in uploaded['assets']}
    for r in manifest['assets']:
        remote=assets[r['name']];assert remote['size']==r['bytes'] and remote['digest']=='sha256:'+r['sha256'] and remote['state']=='uploaded',r['name']
    for name in ['RELEASE-ARTIFACTS.json','SHA256SUMS']:
        local=a.stage/name;remote=assets[name];assert remote['size']==local.stat().st_size and remote['digest']=='sha256:'+hashlib.sha256(local.read_bytes()).hexdigest(),name
    cmd=['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/releases/'+str(release['id']),'--method','PATCH','--input','-']
    result=subprocess.run(cmd,input=json.dumps(dict(draft=False)).encode(),cwd='/tmp',env=host_tool_environment(),capture_output=True,check=True);public=json.loads(result.stdout)
    assert not public['draft'];assert api('git/ref/tags/'+tag)['object']['sha']==target
    receipt=dict(html_url=public['html_url'],tag=tag,release_id=public['id'],source_github_commit=target,confirmed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),assets=manifest['assets'],server_digests_verified=True,delivery_complete=True,functional_demo_ready=False,hardware_ready=False,real_robot_ran=False,necessary_generalization_passed=False,private_media_published=False,goal_complete=False)
    (d/'PUBLIC-DELIVERY-RECEIPT.json').write_text(json.dumps(receipt,indent=2))
    record('newknife_failure_evidence_release_published',str(d/'PUBLIC-DELIVERY-RECEIPT.json'),config={'release':public['html_url'],'assets':len(assets)},updates={'delivery_complete':True,'github_release':public['html_url'],'functional_demo_ready':False,'goal_complete':False},next_step='Verify anonymous downloads and update standalone continuation with remaining functional bottleneck')
    print(json.dumps(receipt))

if __name__=='__main__':main()
