"""Small time-weighted summary of existing real nvidia-smi samples, with gaps."""
import argparse,datetime,json
from pathlib import Path

def summarize(path,hours=4):
 rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()];rows.sort(key=lambda r:r['utc']);end=datetime.datetime.fromisoformat(rows[-1]['utc']);start=end-datetime.timedelta(hours=hours);covered=weighted=0.;gaps=[]
 for first,last in zip(rows[:-1],rows[1:]):
  a=datetime.datetime.fromisoformat(first['utc']);b=datetime.datetime.fromisoformat(last['utc']);lo=max(start,a);hi=min(end,b)
  if hi<=lo:continue
  seconds=(hi-lo).total_seconds()
  if (b-a).total_seconds()>45 or first['exit_code']!=0 or first['whole_machine_sample_mean_percent'] is None:
   gaps.append(dict(start=lo.isoformat(),end=hi.isoformat(),seconds=seconds));continue
  covered+=seconds;weighted+=seconds*first['whole_machine_sample_mean_percent']
 span=(end-start).total_seconds();return dict(window_start_utc=start.isoformat(),window_end_utc=end.isoformat(),covered_seconds=covered,missing_seconds=span-covered,gaps=gaps,time_weighted_observed_percent=weighted/covered if covered else None,missing_counted_zero_percent=weighted/span,whole_machine_4h_floor_percent=26,running_target_percent=40,conservative_floor_met=weighted/span>=26,scope='Real fourGPU15s samples, lastvalueheld only across <=45s observedinterval. Gaps remainunknown and conservativevariant counts themzero. Sampledestimate, not hardwareintegral. No extrapolation beforemonitorstart.')

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=summarize(a.input);a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
