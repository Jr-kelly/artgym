"""Locate sustained departures after arrival under externally fixed goal clocks.

Compare timing relative to each command onset for the same checkpoint at two
command durations. Departures toward the next endpoint are only correlations;
they do not uniquely prove that a policy anticipates a timed command switch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def first_streak(values,length=9,start=0):
    count=0
    for i in range(start,len(values)):
        count=count+1 if values[i] else 0
        if count>=length:return i-length+1
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names',nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    result={}
    for name in args.names:
        path=root/'runs/wuji-goal/verification'/name
        status=json.loads((path/'status.json').read_text())
        assert status['status']=='completed' and status['returncode']==0
        report=json.loads((path/'report.json').read_text())
        with np.load(path/'trace.npz') as archive:
            trace={k:archive[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
        steps=report['protocol']['stage_steps'];dt=report['protocol']['control_dt'];n=report['num_envs']
        assert trace['active'].shape==(600,n)
        records=[]
        for stage in range(600//steps):
            start=stage*steps;end=start+steps
            for i in range(n):
                valid=trace['active'][start:end,i]&~trace['fall'][start:end,i]&~trace['invalid'][start:end,i]
                error=trace['slider'][start:end,i]-trace['goal'][start:end,i]
                pose=(trace['drift'][start:end,i]<.01)&(trace['rotation'][start:end,i]<.25)
                arrival=first_streak((abs(error)<.002)&valid)
                departure=None;toward=None
                if arrival is not None:
                    departure=first_streak((abs(error)>=.002)&valid,start=arrival+9)
                    direction=1 if stage%2 else -1
                    toward=first_streak((error*direction>=.002)&valid,start=arrival+9)
                row=dict(env=i,stage=stage,command='close' if stage%2 else 'open',
                    alive_whole_stage=bool(valid.all()),pose_stable_whole_stage=bool(pose.all()),
                    attained=arrival is not None,held_endpoint=bool(((abs(error)<.002)&valid)[-9:].all()),
                    arrival_streak_start_seconds=None if arrival is None else float(arrival*dt),
                    sustained_departure_seconds=None if departure is None else float(departure*dt),
                    sustained_toward_next_seconds=None if toward is None else float(toward*dt),
                    sustained_toward_next_before2seconds=bool(toward is not None and toward*dt<2),
                    end_signed_error_mm=float(np.median(error[-9:])*1000))
                records.append(row)
        summaries={}
        for command in ['open','close']:
            rows=[r for r in records if r['command']==command]
            arrived=[r for r in rows if r['attained'] and r['alive_whole_stage'] and r['pose_stable_whole_stage']]
            departures=[r for r in arrived if r['sustained_toward_next_seconds'] is not None]
            times=[r['sustained_toward_next_seconds'] for r in departures]
            summaries[command]=dict(command_windows=len(rows),stable_arrived_windows=len(arrived),
                stable_arrived_notheld=sum(not r['held_endpoint'] for r in arrived),
                sustained_toward_next=len(departures),toward_next_before2seconds=sum(r['sustained_toward_next_before2seconds'] for r in departures),
                departure_time_median_seconds=float(np.median(times)) if times else None,
                departure_time_p10_p90_seconds=np.quantile(times,[.1,.9]).tolist() if times else None)
        result[name]=dict(checkpoint_sha256=report['checkpoint_sha256'],stage_seconds=steps*dt,
            summaries=summaries,records=records,
            input_sha256={f:hashlib.sha256((path/f).read_bytes()).hexdigest() for f in ['report.json','trace.npz','status.json']})
    args.output.write_text(json.dumps(dict(scope=__doc__,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results=result),indent=2)+'\n')
    for name,data in result.items():print(json.dumps(dict(name=name,summaries=data['summaries'])))


if __name__=='__main__':main()
