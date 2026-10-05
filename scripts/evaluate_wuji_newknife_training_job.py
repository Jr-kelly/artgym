"""Bounded final-checkpoint watcher and two-profile native development replay."""
import argparse,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--operation-prepared',type=Path);p.add_argument('--training',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True);checkpoint=a.training/'update_000100.pth';deadline=time.monotonic()+1200
 while not (a.training/'complete.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('Training completion not observed; do not replay incomplete checkpoint')
  time.sleep(10)
 sha=hashlib.sha256(checkpoint.read_bytes()).hexdigest();assert sha==checkpoint.with_suffix('.sha256').read_text().strip();rows=[]
 def event(name,**kw):
  with (a.output/'events.jsonl').open('a') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=name,checkpoint_sha256=sha,**kw))+'\n')
 for profile in ['constant','variable']:
  output=a.output/profile;cmd=[sys.executable,'-m','scripts.run_wuji_newknife','--checkpoint',str(checkpoint),'--resistance','research/newknife-20261005/resistance-'+profile+'.json','--no-video','--output',str(output)];cmd+=['--operation-prepared',str(a.operation_prepared)] if a.operation_prepared else [];event('native_development_replay_started',profile=profile,command=cmd)
  with (a.output/(profile+'.log')).open('w') as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
  ev=output/'simulation/newknife-evaluation.json';row=dict(profile=profile,exit_code=code,trial=str(output/'simulation'),evaluation=json.loads(ev.read_text()) if ev.exists() else None);rows.append(row);event('native_development_replay_finished',profile=profile,exit_code=code,evidence=str(ev),pass_all=row['evaluation']['pass_all'] if row['evaluation'] else None)
 result=dict(scope=__doc__,training=str(a.training),checkpoint=str(checkpoint),checkpoint_sha256=sha,rows=rows,independent_validation=False,hardware=False);(a.output/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
