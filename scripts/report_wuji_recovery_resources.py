"""Time-weighted all-device utilization with explicit gaps and four-hour coverage."""
import argparse,datetime,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--history',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[]
    for line in a.history.read_text().splitlines():
        r=json.loads(line)
        if 'gpus' not in r:continue
        values={}
        for gpu in r['gpus'].splitlines():
            index,util,memory=gpu.split(',');values[int(index)]=float(util.strip().rstrip('%'))
        if len(values)!=4:continue
        rows.append((datetime.datetime.fromisoformat(r['time']).timestamp(),values))
    assert len(rows)>1 and all(b[0]>a[0] for a,b in zip(rows,rows[1:]))
    end=rows[-1][0]
    def integrate(start):
        totals=[0.]*4;covered=0.;gaps=0.
        for (t,values),(next_t,_) in zip(rows,rows[1:]):
            dt=max(0,min(next_t,end)-max(t,start))
            if next_t-t>15:gaps+=dt;continue
            covered+=dt
            for gpu in range(4):totals[gpu]+=values[gpu]*dt
        return dict(covered_seconds=covered,gap_seconds=gaps,device_mean_percent=[x/covered for x in totals] if covered else None,machine_mean_percent=sum(totals)/(4*covered) if covered else None)
    full=integrate(rows[0][0]);rolling=integrate(max(rows[0][0],end-14400));span=end-rows[0][0]
    result=dict(first_sample_utc=datetime.datetime.fromtimestamp(rows[0][0],datetime.timezone.utc).isoformat(),last_sample_utc=datetime.datetime.fromtimestamp(end,datetime.timezone.utc).isoformat(),samples=len(rows),elapsed_seconds=span,full_observed_window=full,last_up_to_four_hours=rolling,has_complete_four_hour_coverage=span>=14400 and rolling['gap_seconds']==0,scope='Four physical H200 devices, including unused devices. Time-weighted zero-order hold between samples, gaps over15s excluded and disclosed. GPU occupied job wall budget is accounted separately; utilization does not justify filler computation.')
    result['four_hour_26percent_met']=rolling['machine_mean_percent']>=26 if result['has_complete_four_hour_coverage'] else None
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
