"""Timed whole-machine utilization, conservatively zero across unsampled gaps."""
import argparse,datetime,json,re
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];d=root/'research/geometry-generalization-20261002';now=datetime.datetime.now(datetime.timezone.utc).timestamp();start=now-14400;records={};paths=[root.parent/'unified-student-20261001/research/unified-student-20261001/resources.jsonl',d/'resources.jsonl']
 for path in paths:
  if not path.exists():continue
  for line in path.read_text().splitlines():
   try:r=json.loads(line);t=datetime.datetime.fromisoformat(r['utc']).timestamp()
   except (ValueError,KeyError):continue
   if r.get('remote_exit')!=0 or t<start-90:continue
   vals=[];uuids=[]
   for line in r.get('remote','').splitlines():
    match=re.match(r'^([0-3]), (GPU-[^,]+), (\d+) %, (\d+) MiB',line)
    if match:uuids.append(match.group(2));vals.append(int(match.group(3)))
   if len(vals)==4:records[t]=dict(util=vals,uuids=uuids,source=str(path))
 timestamps=sorted(records);assert timestamps
 current_uuid=records[timestamps[-1]]['uuids'];integral=0.;covered=0.;intervals=[]
 for i,t in enumerate(timestamps):
  if records[t]['uuids']!=current_uuid:continue
  # Retain one sample for at most its monitor cadence; no interpolation over
  # the previous round's monitor shutdown and this round's startup gap.
  cadence=20 if records[t]['source']==str(d/'resources.jsonl') else 65
  end=min(t+cadence,timestamps[i+1] if i+1<len(timestamps) else now,now);begin=max(t,start)
  if end<=begin:continue
  seconds=end-begin;covered+=seconds;integral+=seconds*sum(records[t]['util'])/4
  intervals.append(dict(start_utc=datetime.datetime.fromtimestamp(begin,datetime.timezone.utc).isoformat(),seconds=seconds,util=records[t]['util']))
 result=dict(checked_utc=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat(),window_seconds=14400,same_machine_gpu_uuids=current_uuid,known_seconds=covered,unknown_seconds=14400-covered,whole_machine_mean_known=integral/covered if covered else None,four_hour_lower_bound=integral/14400,minimum26_lower_bound_pass=integral/14400>=26,target40_lower_bound_pass=integral/14400>40,last_sample_utc=datetime.datetime.fromtimestamp(timestamps[-1],datetime.timezone.utc).isoformat(),last_sample_util=records[timestamps[-1]]['util'],inputs=[str(x) for x in paths],method='Integrate same-UUID timestamped4GPU samples; unknown intervals treated0. This is utilization evidence, not extraGPUbudget. Previousround history never assumed currentprocess.',intervals=intervals)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='intervals'}))
if __name__=='__main__':main()
