"""Rescore shared-policy raw traces with separate results for each source grasp."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.wuji_arrival_metrics import score_arrival_trace
from scripts.summarize_wuji_multigrasp_trace import summarize
from scripts.summarize_wuji_hold_stages import stages,grouped
from scripts.evaluate_wuji_hold import ROOT,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    run=json.loads(a.results.read_text());assert run['status']=='completed';plan=run['plan']
    a.output.mkdir(parents=True,exist_ok=False);rows=[];summary=[];endpoint=[]
    count=plan['trials_per_source'];sources=plan['sources'];expected=count*len(sources)
    for item in run['results']:
        saved=item['report'];model=item['model'];protocol=item['protocol'];path=ROOT/item['evidence']/'trace.npz'
        assert saved['initial_states_sha256']==plan['final_states_sha256']
        if model!='static':assert saved['checkpoint_sha256']==plan['models'][model]['sha256']
        with np.load(path) as archive:trace={key:archive[key] for key in archive.files}
        assert trace['active'].shape[1]==expected
        score=score_arrival_trace(trace,600,.01) if protocol=='arrival' else score_timed_trace(trace,150 if protocol=='fixed5' else 60,9,600)
        for key,value in score.items():assert saved[key]==value,(model,protocol,key)
        for i,source in enumerate(sources):
            section={key:value[:,i*count:(i+1)*count] for key,value in trace.items()}
            body=(section['active']&~section['fall']&~section['invalid']).all(0)&(section['drift']<.01).all(0)&(section['rotation']<.25).all(0)&(len(section['active'])==600)
            records=score['records'][i*count:(i+1)*count]
            metric='three_cycles' if protocol=='arrival' else 'stable_full_all_endpoints'
            for j,record in enumerate(records):rows.append(dict(source=source,model=model,protocol=protocol,trial=j,success=record[metric],alive=record['alive_full'],body_stable=bool(body[j])))
            summary.append(dict(source=source,model=model,protocol=protocol,n=count,success=sum(r[metric] for r in records),alive=sum(r['alive_full'] for r in records),body_stable=int(body.sum()),trace_sha256=sha(path)))
            if protocol in ['fixed2','fixed5']:
                step=150 if protocol=='fixed5' else 60
                independent=summarize(section,step)
                assert [x['strict'] for x in independent]==[x[metric] for x in records]
                endpoint.extend(dict(source=source,model=model,protocol=protocol,**x) for x in grouped(stages(section,step)))
    with (a.output/'trials.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    result=dict(status='independently_rescored',plan=plan,summaries=summary,endpoint_diagnostics=endpoint,
                scope='One shared policy versus same-parent singleton continuation and preserved historical reference. Per-source perturbations of trained base grasps; no unseen-grasp or hardware claim. All final weights predeclared, no final-data selection.')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
