"""Account owned job wall-clock GPU reservations and deduplicated host samples."""
import argparse,json,datetime
from pathlib import Path

def stamp(x):return datetime.datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];base=root/'runs/unified-policy-20260930';now=datetime.datetime.now(datetime.timezone.utc);jobs=[];samples=[]
 for f in base.glob('*/status.json'):
  s=json.loads(f.read_text());elapsed=float(s.get('wall_seconds',s.get('elapsed_seconds',0)));command=' '.join(s.get('command',[]))
  role='offline_training' if 'scripts.train_wuji_unified_bc' in command else 'expert_collection' if 'scripts.collect_wuji_unified_training' in command else 'demonstration' if '--video' in command else 'evaluation_or_preflight'
  jobs.append(dict(name=s['name'],status=s['status'],gpu=s['gpu'],started=s['started'],finished=s.get('finished'),gpu_hours=elapsed/3600,role=role))
  g=f.parent/'gpu.jsonl'
  if g.exists() and not s['name'].startswith('local-'):
   for line in g.read_text().splitlines():
    try:
     d=json.loads(line);rows=d['gpus'].strip().splitlines();values=[float(x.split(',')[1].strip().replace('%','')) for x in rows];samples.append((stamp(d['time']),sum(values)/len(values)))
    except (ValueError,KeyError):pass
 fine=base/'machine-gpu-history.jsonl'
 if fine.exists():
  high=[]
  for line in fine.read_text().splitlines():
   try:
    d=json.loads(line);values=[float(x.split(',')[1].strip().replace('%','')) for x in d['gpus'].strip().splitlines()];high.append((stamp(d['time']),sum(values)/len(values)))
   except (ValueError,KeyError):pass
  if high:samples=[x for x in samples if x[0]<min(t for t,v in high)]+high
 samples.sort();dedup=[]
 for t,value in samples:
  if not dedup or t-dedup[-1][0]>=4:dedup.append((t,value))
 area=duration=0
 for (t,v),(u,w) in zip(dedup,dedup[1:]):
  if 0<u-t<=90:area+=(u-t)*v;duration+=u-t
 result=dict(recorded_utc=now.isoformat(),jobs=jobs,owned_reserved_gpu_hours=sum(x['gpu_hours'] for x in jobs),training_reserved_gpu_hours=sum(x['gpu_hours'] for x in jobs if x['role']=='offline_training'),remote_observed_machine_mean_gpu_utilization_percent=area/duration if duration else None,remote_sample_covered_seconds=duration,remote_sample_count=len(dedup),full_four_hour_window_covered=duration>=14400,note='Uses five-second monitor when available, retains older coarse prefix. Includes job startup/I/O reservations conservatively; active jobs charged through last heartbeat. Host utilization averages all4cards, deduplicates dual-wrapper samples; missing time not asserted measured. CUDA smoke and offline short audit additionally tracked separately.')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='jobs'}))
if __name__=='__main__':main()
