"""Explain reached-but-not-held fixed-time command failures from physical traces."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names',nargs='+')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    names=args.names or ['precision125-teacher-timed2seconds-perturb100',
           'precision-cont-cost1-cp25-timed2seconds-perturb100',
           'precision125-student-timed2seconds-perturb100']
    result={}
    for name in names:
        p=root/'runs/wuji-goal/verification'/name
        trace=np.load(p/'trace.npz');report=json.loads((p/'report.json').read_text())
        n=report['num_envs'];steps=report['protocol']['stage_steps'];dt=report['protocol']['control_dt']
        rows=[]
        for stage in range(600//steps):
            a,b=stage*steps,(stage+1)*steps
            pos,goal=trace['slider'][a:b],trace['goal'][a:b]
            valid=trace['active'][a:b]&~trace['fall'][a:b]&~trace['invalid'][a:b]
            hit=(abs(pos-goal)<.002)&valid
            streak=np.zeros(n,int);first=np.full(n,-1,int)
            for i,h in enumerate(hit):
                streak=(streak+1)*h;new=(streak>=9)&(first<0);first[new]=i
            held=hit[-9:].all(0);attained=first>=0
            err=(pos-goal)[-9:];q=trace['q'][a:b];target=trace['target'][a:b];action=trace['action'][a:b]
            peak_after=np.array([np.max(abs(pos[first[e]:,e]-goal[first[e]:,e])) if first[e]>=0 else np.nan for e in range(n)])
            rows.append(dict(stage=stage,command='open' if stage%2==0 else 'close',attained=int(attained.sum()),
                held=int(held.sum()),reached_then_failed_endpoint=int((attained&~held).sum()),
                median_arrival_seconds=float(np.median((first[attained]+1)*dt)),
                end_error_median_mm=float(np.median(err)*1000),end_error_p10_p90_mm=(np.quantile(err,[.1,.9])*1000).tolist(),
                median_peak_error_after_arrival_mm=float(np.nanmedian(peak_after)*1000),
                thumb_action_abs_mean=float(abs(action[-9:,:,16:]).mean()),
                thumb_target_error_mean_rad=float(abs(target[-9:,:,16:]-q[-9:,:,16:]).mean())))
        result[name]=dict(trace_sha256=hashlib.sha256((p/'trace.npz').read_bytes()).hexdigest(),
            report_sha256=hashlib.sha256((p/'report.json').read_bytes()).hexdigest(),rows=rows)
    output=args.output or root/'runs/wuji-goal/diagnostics/timed-goal-failure-components.json'
    output.write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results=result,
        scope='Recordedfixed2scommands;nopolicyorphysicschange;positivecloseerrorisreopening;correlationsdonotproveuniquephysicalcause'),indent=2)+'\n')
    for name,data in result.items():print(name,[(r['command'],r['attained'],r['held']) for r in data['rows']])


if __name__=='__main__':main()
