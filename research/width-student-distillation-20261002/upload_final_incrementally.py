"""Upload completed immutable final packets; never overwrite v1 evidence."""
import json,os,subprocess,time
from scripts.record_wuji_width_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment
release=json.loads((D/'FINAL_RELEASE_DRAFT.json').read_text())['id'];dest=R/'delivery/width-student-distillation-20261002';deadline=time.monotonic()+14400;uploaded=[]
e=host_tool_environment();e['PATH']='/home/agiuser/.local/bin:'+e.get('PATH','');e['PYTHONPATH']='.'
while time.monotonic()<deadline:
 for receipt in sorted(dest.glob('width-final-*-raw-v2.receipt.json')):
  r=json.loads(receipt.read_text());name=r['name'];verification=D/('UPLOAD_'+name+'.json')
  if verification.exists():continue
  assert r['size']<1500000000
  subprocess.run(['python3','research/unified-student-20261001/upload_streamed_release_assets.py','--release-id',str(release),'--verification',str(verification),'--max-time','1200',str(R/r['archive'])],env=e,cwd=R,check=True,timeout=1250)
  uploaded.append(name)
 if len(list(D.glob('UPLOAD_width-final-*-raw-v2.json')))==15:break
 time.sleep(20)
record('final_raw_incremental_upload_finished',release_id=release,verified_packets=len(list(D.glob('UPLOAD_width-final-*-raw-v2.json'))),next='Publish final release only after independent analysis and evidence verification')
