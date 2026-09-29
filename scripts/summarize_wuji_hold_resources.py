"""Integrate observed utilization, explicitly reporting missing four-hour coverage."""
import argparse
import datetime
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def timestamp(value):
    return datetime.datetime.fromisoformat(value).timestamp()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    samples=[]
    for line in (ROOT/'research/hold-20260929/receipts/gpu-history.jsonl').read_text().splitlines():
        row=json.loads(line)
        values={int(parts[0]):float(parts[1].strip().rstrip('%'))/100
                for parts in (line.split(',') for line in row['gpu'].splitlines())}
        assert len(values)==4
        samples.append((timestamp(row['time']),values))
    samples.sort()
    def integrate(start,end,gpu=None):
        covered=busy=0.
        for (left,values),(right,_) in zip(samples,samples[1:]):
            if right-left>120:continue
            dt=max(0.,min(end,right)-max(start,left))
            covered+=dt
            busy+=dt*(sum(values.values())/4 if gpu is None else values[gpu])
        duration=end-start
        return dict(requested_seconds=duration,covered_seconds=covered,
            coverage_pct=100*covered/duration if duration else None,
            observed_time_weighted_utilization_pct=100*busy/covered if covered else None,
            lower_bound_if_missing_samples_idle_pct=100*busy/duration if duration else None)
    last=samples[-1][0];jobs=[]
    latest=json.loads((ROOT/'research/hold-20260929/receipts/monitor-latest.json').read_text())
    for name,state in latest['jobs'].items():
        command=state.get('command',[])
        if not any('scripts.train_' in part for part in command):continue
        start=timestamp(state['started']);end=timestamp(state['finished']) if state.get('finished') else last
        jobs.append(dict(name=name,status=state['status'],gpu=state['gpu'],started=state['started'],
            finished=state.get('finished'),allocation_hours=max(0,end-start)/3600,
            measured=integrate(start,end,state['gpu'])))
    result=dict(as_of_utc=latest['time'],latest_four_hours=integrate(last-14400,last),
        full_observed_interval=integrate(samples[0][0],last),jobs=jobs,
        total_training_allocation_hours=sum(row['allocation_hours'] for row in jobs),
        scope='Whole-machine mean of all four GPUs, including idle devices. No interpolation over >120s gaps. Coverage and zero-filled lower bound accompany observed mean; incomplete coverage is not a full four-hour platform measurement. Allocation is wall time including startup, not kernel profiler time.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
