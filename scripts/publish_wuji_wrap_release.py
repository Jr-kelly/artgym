"""Publish the explicitly authorized prepared release after its minimum work time.

This does not mark behavior/generalization/hardware goals complete. Archive
STATE is the preparation snapshot; a separate public receipt records delivery.
"""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
from scripts.host_tool_environment import host_tool_environment
from scripts.publish_wuji_wrap_snapshot import api
from scripts.record_wuji_wrap_goal import record,D,R

def patch(path,payload):
 cmd=['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/'+path,'--method','PATCH','--input','-']
 result=subprocess.run(cmd,input=json.dumps(payload).encode(),cwd='/tmp',env=host_tool_environment(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);return json.loads(result.stdout)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',type=Path,required=True);a=p.parse_args();state=json.loads((D/'STATE.json').read_text());now=datetime.datetime.now(datetime.timezone.utc);start=datetime.datetime.fromisoformat(state['round_start_utc']);minimum=datetime.datetime.fromisoformat(state['minimum_finish_utc']);assert now>=minimum and (now-start).total_seconds()>=12*3600,'Useful current round has not reached requested minimum time; no early formal publication'
 draft=json.loads((D/'RELEASE-DRAFT.json').read_text());release=api('releases/'+str(draft['id']));assert release['draft'] and release['tag_name']==draft['tag'];manifest=json.loads((a.stage/'RELEASE-ARTIFACTS.json').read_text());assets={x['name']:x for x in release['assets']}
 for row in manifest['assets']:
  remote=assets[row['name']];assert remote['state']=='uploaded' and remote['size']==row['bytes'] and remote['digest']=='sha256:'+row['sha256']
 target=draft['target_github_commit'];assert release['target_commitish']==target
 # Public final code includes science changes; archived metadata predates
 # publication. Keep that distinction explicit instead of forging a timestamp.
 body=(D/'RELEASE-NOTES.md').read_text()+'\n\n归档中的STATE是制作时的快照。正式交付完成以PUBLIC-DELIVERY-RECEIPT.json及最新独立DELIVERY-RESULTS.json为准；目标/测力/泛化/硬件标志不因发布变为成功。\n'
 release=patch('releases/'+str(draft['id']),dict(draft=False,body=body));assert not release['draft'] and release['published_at'];tagref=api('git/ref/tags/'+draft['tag']);assert tagref['object']['type']=='commit' and tagref['object']['sha']==target
 receipt=dict(release_id=release['id'],tag=release['tag_name'],html_url=release['html_url'],published_at=release['published_at'],confirmed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_github_commit=target,source_git_tree=api('git/commits/'+target)['tree']['sha'],elapsed_hours=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()/3600,minimum_work_hours=12,assets_initially_verified=len(release['assets']),delivery_complete=True,functional_demo_ready=True,necessary_generalization_resolved=False,axial_force_measurement_resolved=False,hardware_ready=False,real_robot_ran=False,goal_complete=False,archive_state_scope='Pre-publication preparation snapshot; this receipt records publication independently',remaining_blockers='Original axialB/railC unavailable; high-load and jointgeneralizationfail; realresistance/effectivefullreturn/SDK inputs missing')
 (D/'PUBLIC-DELIVERY-RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');record('github_public_release_published',evidence='research/wrap-force-20261004/PUBLIC-DELIVERY-RECEIPT.json',conclusion='NewformalReleasepublicafter>=12h usefulcurrentround. Exacttag/sciencetree verified; deliverytrueonly, goal/generalization/originalforce/hardwarefalse.',phase='Formal release delivered; publication receipts and final standalone metadata being verified',state_updates={'delivery_complete':True,'functional_demo_ready':True,'necessary_generalization_resolved':False,'axial_force_measurement_resolved':False,'hardware_ready':False,'real_robot_ran':False,'goal_complete':False,'github_release':release['html_url']},next='Upload completedpublicreceipt andupdatedstandalone metadata/checksums; verify anonymouspublicvisibility andsource/assetdigest')
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
