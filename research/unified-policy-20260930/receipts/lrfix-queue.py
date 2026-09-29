import os,time,subprocess,json,datetime
from pathlib import Path
r=Path('/tmp/artgym-unified-policy-20260930');os.chdir(r);b=r/'runs/unified-policy-20260930';end=time.time()+600
while not (b/'bc-unified-normfix-s3001-seg1-segment-completed.json').exists():
 if time.time()>end:raise TimeoutError('Previous bounded segment did not complete; do not launch')
 time.sleep(2)
cmd=['/tmp/wuji-unified-runtime/bin/python','-m','scripts.run_wuji_unified_c_segment','--name','bc-unified-lrfix-s3001-seg1','--init','runs/unified-policy-20260930/experts/historical.pth','--lr','.0001']
with (b/'bc-unified-lrfix-s3001-seg1-orchestration.log').open('w') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(b/'lrfix-queue-launched.json').write_text(json.dumps(dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd))+'\n')
