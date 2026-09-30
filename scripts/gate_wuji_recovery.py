"""Preregistered F/S gates and checkpoint ordering from independently rescored data."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--reports',type=Path,nargs='+',required=True);p.add_argument('--experts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[]
    for path in a.reports:rows+=json.loads(path.read_text())['rows']
    experts=json.loads(a.experts.read_text())['rows'];lookup={(r['model'],r['protocol'],r['source']):r for r in experts};out=[]
    for model in sorted(set(r['model'] for r in rows)):
        if model in ['static','historical','source3']:continue
        selected=[r for r in rows if r['model']==model];strict=[r for r in selected if r['protocol'] in ['S2','S5']];functional=[r for r in selected if r['protocol']=='F'];assert len(strict)==8 and len(functional)==4
        cells=[]
        for r in strict:
            e=lookup[('source3' if r['source']==3 else 'historical',r['protocol'],r['source'])]
            assert r['n']==e['n'],'Compare equally sized cohorts; rerun experts for64/final'
            values={'strict_absolute':r['rate']-.8,'body_absolute':r['body_rate']-.95,'strict_relative':r['rate']-e['rate']+.1,'body_relative':r['body_rate']-e['body_rate']+.03}
            cells.append(dict(source=r['source'],protocol=r['protocol'],n=r['n'],margins=values,passed=all(v>=-1e-12 for v in values.values()),within_one_episode=all(v>=-1/r['n']-1e-12 for v in values.values())))
        passed=all(c['passed'] for c in cells);near=all(c['within_one_episode'] for c in cells)
        out.append(dict(model=model,F_passed=all(r['rate']>=.8 for r in functional),S_passed=passed,cohort_n=strict[0]['n'],promotion64_indicated=strict[0]['n']==32 and (passed or near),student_or_second_seed_eligible=passed and strict[0]['n']>=64,worst_strict=min(r['rate'] for r in strict),worst_phase_hold=min(r['phase_hold_rate'] for r in strict),worst_body=min(r['body_rate'] for r in strict),mean_slider_error_m=sum(r['phase_error_mean_m'] for r in strict)/8,cells=cells))
    out.sort(key=lambda r:(-r['worst_strict'],-r['worst_phase_hold'],-r['worst_body'],r['mean_slider_error_m'],r['model']))
    result=dict(models=out,ordering='Worst S success, worst phase endpoint hold, worst body; common closed-loop slider error for cross-family ties. BC within-family offline joint-target fit remains diagnostic/tie evidence. No incomparable raw mu loss ranking.',promotion_note='Within one episode at32 only triggers a64 check, never labels32 as passed; full64 exact thresholds required before second seed/student.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([{k:r[k] for k in ['model','F_passed','S_passed','promotion64_indicated','worst_strict','worst_phase_hold','worst_body']} for r in out]))
if __name__=='__main__':main()
