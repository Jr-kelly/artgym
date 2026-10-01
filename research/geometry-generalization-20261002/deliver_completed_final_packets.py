"""Bounded CPU delivery watcher; never starts/retries scientific GPU work."""
import json,subprocess,sys,time
from pathlib import Path
from scripts.record_wuji_geometry_goal import R,D,record
labels=list(json.loads((D/'ASSETS.json').read_text()));root=R/'runs/geometry-generalization-20261002';started=time.monotonic();pending=set(labels)
record('bounded_final_delivery_watcher_started',max_seconds=5400,labels=labels,next='Deliver only completed six-protocol final geometry packets; errors stop delivery for review')
while pending and time.monotonic()-started<5400:
 for label in labels:
  if label not in pending:continue
  job=root/'jobs'/('final-'+label+'-batch');result=job/'result.json'
  if not result.exists():continue
  receipt=json.loads(result.read_text());assert receipt['exit_code']==0,(label,receipt['exit_code'])
  paths=[]
  for name in [label+'-static-final']+['final-'+label+'-'+m+'-'+p for m in ['teacher','student'] for p in ['S2','S5','F']]:
   dest=root/name
   subprocess.run(['rsync','-az','-e','ssh -p33024','wangjiarui@10.13.160.5:/tmp/artgym-geometry-20261002/runs/geometry-generalization-20261002/'+name+'/',str(dest)+'/'],check=True,timeout=600)
   paths.append(str(dest.relative_to(R)))
  assert all((root/('final-'+label+'-'+m+'-'+p)/'geometry-receipt.json').exists() for m in ['teacher','student'] for p in ['S2','S5','F'])
  paths.append(str(job.relative_to(R)));name='geometry-final-'+label
  subprocess.run([sys.executable,'-m','scripts.archive_wuji_geometry','--name',name,'--paths']+paths,cwd=R,check=True,timeout=600)
  verification=D/('upload-final-'+label+'.json');archive=R/'delivery/geometry-generalization-20261002'/(name+'.tar.gz');assert archive.stat().st_size<1500000000
  subprocess.run([sys.executable,str(R/'research/unified-student-20261001/upload_streamed_release_assets.py'),'--release-id','401374769','--verification',str(verification),str(archive)],cwd=R,check=True,timeout=360)
  record('completed_final_geometry_packet_delivered',geometry=label,evidence=str(verification.relative_to(R)),final_data='Already frozen evaluation only; no model/recipe reselection',next='Continue remaining finite final jobs, then independently rescore all78')
  pending.remove(label)
 if pending:time.sleep(20)
assert not pending,sorted(pending)
record('all_final_geometry_packets_delivered',conditions=len(labels),next='Independently rescore78 final protocol runs and finish report/public verification')
