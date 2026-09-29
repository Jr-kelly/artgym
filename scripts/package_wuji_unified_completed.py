"""Archive an explicitly frozen list of completed stages, sequentially on CPU."""
import datetime,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'runs/unified-policy-20260930';D=R/'delivery/unified-policy-20260930';Q=R/'research/unified-policy-20260930'
def event(kind,**kw):
 e=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=kind,**kw)
 for p in [Q/'DECISIONS.jsonl',Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/journal/events.jsonl')]:
  with p.open('a') as f:f.write(json.dumps(e)+'\n')
 for p in [Q/'HANDOFF.md',Path('/data/research/artgym/WUJI_GOAL_HANDOFF.md')]:
  with p.open('a') as f:f.write('\n'+e['utc']+' '+kind+' '+json.dumps(kw)+'\n')
 print(json.dumps(e),flush=True)
def main():
 groups={
 'train-t5':['train-data-t5'],
 'g0':['g0-t2','g0-t5','g0-regression-t2','g0-regression-t5','g0-promotion-t2','g0-promotion-t5'],
 'g1':['g1-development-t2','g1-development-t5','g1-promotion-t2','g1-promotion-t5'],
 'pilots':['bc-pilot-historical','bc-pilot-source3','bc-pilot-source3-lr4','bc-pilot-source3-lr5'],
 'baseline-historical':[x.name for x in B.glob('bc-unified-historical-s3001-seg1*')],
 'baseline-source3':[x.name for x in B.glob('bc-unified-source3-s3001-seg1*')],
 }
 for name,names in groups.items():
  asset='wuji-unified-'+name
  if (D/(asset+'.receipt.json')).exists():continue
  for n in names:
   if (B/(n+'-job')).exists() and n+'-job' not in names:names.append(n+'-job')
  paths=[str((B/n).relative_to(R)) for n in sorted(set(names))]
  event('archive_started',name=asset,paths=paths,next='Hash and retain all raw results and resumable checkpoints; no GPU work')
  result=subprocess.run([sys.executable,'-m','scripts.archive_wuji_unified','--name',asset,'--paths',*paths],cwd=R)
  if result.returncode: event('archive_failed',name=asset,returncode=result.returncode);raise SystemExit(result.returncode)
  event('archive_completed',**json.loads((D/(asset+'.receipt.json')).read_text()),next='Restore-check and upload release; retain local originals')
if __name__=='__main__':main()
