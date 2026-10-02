"""Registered P/C/G/teacher comparisons with raw rescore and paired episode units."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import numpy as np
from scripts.analyze_wuji_geometry import read_run, paired_ci
from scripts.summarize_wuji_unified import wilson
from scripts.wuji_width_contract import sha


def time_parts(directory):
    with np.load(directory/'trace.npz') as z:
        t={k:z[k] for k in ['active','fall','invalid','drift','rotation','slider','goal']}
    T,N=t['active'].shape
    valid=t['active']&~t['fall']&~t['invalid']
    pose=(t['drift']<.01)&(t['rotation']<.25)
    error=abs(t['slider']-t['goal']);phase=np.zeros(N,int);streak=np.zeros(N,int)
    completions=np.zeros((2,N),int);contained=np.zeros((2,N),int);open_in_part=np.zeros(N,bool)
    reached=np.zeros((2,N),int)
    for k in range(T):
        if k==600:open_in_part[:]=False
        part=int(k>=600);streak=np.where(valid[k]&(error[k]<.01),streak+1,0);ready=streak>=45
        close=ready&(phase==1);opened=ready&(phase==0)
        completions[part]+=close;contained[part]+=close&open_in_part
        reached[0]+=opened;reached[1]+=close
        open_in_part[opened]=True;open_in_part[close]=False
        phase[ready]=1-phase[ready];streak[ready]=0
    rows=[]
    for i in range(N):
        row=dict(open_commands_reached=int(reached[0,i]),close_commands_reached=int(reached[1,i]))
        for part,(start,end) in enumerate([(0,600),(600,1200)]):
            suffix='first20' if part==0 else 'last20'
            row['holding_'+suffix]=bool(T>=end and (valid[start:end,i]&pose[start:end,i]).all())
            row['cycle_completions_'+suffix]=int(completions[part,i])
            row['contained_open_close_'+suffix]=int(contained[part,i])
        rows.append(row)
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();plan=json.loads(a.manifest.read_text());episodes=[];seen=set();run_keys=set()
    assert plan['historical_final_access'] is False
    for run in plan['runs']:
        directory=Path(run['directory']);selection_path=Path(run['selection'])
        receipt=json.loads((directory/'geometry-receipt.json').read_text())
        report=json.loads((directory/'report.json').read_text())
        assert receipt['research_dir']=='research/width-student-distillation-20261002'
        assert report['initial_states_sha256']==run['states_sha256']
        assert sha(selection_path)==run['selection_sha256']
        assert sha(directory/'trace.npz')==run['trace_sha256']
        assert receipt['protocol']==run['protocol'] and receipt['asset']['parameters']['label']==run['geometry']
        key=(run['model_sha256'],run['states_sha256'],run['protocol'])
        assert key not in run_keys, 'Duplicate protocol/cohort/model cannot expand denominators'
        run_keys.add(key)
        models=dict(teacher=plan['teacher_sha256'],student=run['model_sha256'])
        if run['role']=='teacher':assert run['model_sha256']==plan['teacher_sha256'] and receipt['model']=='teacher'
        else:assert receipt['model']=='student' and receipt['student_checkpoint_sha256']==run['model_sha256']
        rows=read_run(directory,json.loads(selection_path.read_text()),models)
        extras=time_parts(directory) if run['protocol']=='F' else [{} for _ in rows]
        for row,extra in zip(rows,extras):
            row.update(model=run['role'],model_sha256=run['model_sha256'],joint_success=row['success'] and row['body_stable'],**extra)
            identity=(row['model_sha256'],row['cohort_sha256'],row['protocol'],row['attempt_row'])
            assert identity not in seen;seen.add(identity);episodes.append(row)
    assert episodes, 'No completed physical evidence; do not create empty success statistics'
    cells=[];paired=[]
    for g,m,p,s in sorted({(t['geometry'],t['model'],t['protocol'],t['source']) for t in episodes}):
        rows=[t for t in episodes if (t['geometry'],t['model'],t['protocol'],t['source'])==(g,m,p,s)]
        row=dict(geometry=g,model=m,protocol=p,source=s,n=len(rows))
        for metric in ['success','body_stable','joint_success']:
            k=sum(t[metric] for t in rows);row[metric]=dict(k=k,n=len(rows),rate=k/len(rows),wilson95=wilson(k,len(rows)))
        cells.append(row)
    for g,p,s in sorted({(t['geometry'],t['protocol'],t['source']) for t in episodes}):
        by_model={m:{t['attempt_row']:t for t in episodes if (t['geometry'],t['model'],t['protocol'],t['source'])==(g,m,p,s)} for m in {t['model'] for t in episodes}}
        for left,right in itertools.combinations(sorted(by_model),2):
            x=by_model[left];y=by_model[right]
            if not x or not y:continue
            assert x.keys()==y.keys(), 'Missing paired rows must be resolved explicitly'
            ids=sorted(x);assert all(x[i]['cohort_sha256']==y[i]['cohort_sha256'] for i in ids)
            row=dict(geometry=g,protocol=p,source=s,left=left,right=right,n=len(ids))
            for metric in ['success','body_stable','joint_success']:
                vx=np.asarray([x[i][metric] for i in ids]);vy=np.asarray([y[i][metric] for i in ids]);difference=vy.astype(int)-vx.astype(int)
                row[metric]=dict(both_success=int((vx&vy).sum()),left_only=int((vx&~vy).sum()),right_only=int((~vx&vy).sum()),both_fail=int((~vx&~vy).sum()),right_minus_left=float(difference.mean()),paired_bootstrap95=paired_ci(difference))
            paired.append(row)
    coverage=[dict(geometry=g,model=m,protocol=p,covered_sources=[r['source'] for r in cells if (r['geometry'],r['model'],r['protocol'])==(g,m,p)],
                   missing_sources=sorted(set(range(4))-{r['source'] for r in cells if (r['geometry'],r['model'],r['protocol'])==(g,m,p)}))
              for g,m,p in sorted({(t['geometry'],t['model'],t['protocol']) for t in episodes})]
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'report.json').write_text(json.dumps(dict(cells=cells,paired=paired,coverage=coverage,manifest_sha256=sha(a.manifest),
        unit='episode; protocols/checkpoints reuse states and are correlated',time_scope='20s contained cycles distinguish a cycle opened before20s from one fully in the second half',independent_rescore=True),indent=2)+'\n')
    fields=list(dict.fromkeys(k for row in episodes for k in row))
    with (a.output/'episodes.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(episodes)


if __name__=='__main__':main()
