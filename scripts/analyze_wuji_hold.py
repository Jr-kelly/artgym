"""Independently rescore frozen hold traces and paired within-source contrasts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.wuji_arrival_metrics import score_arrival_trace
from scripts.summarize_wuji_multigrasp_trace import summarize
from scripts.summarize_wuji_hold_stages import stages, grouped

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);trials=[];summaries=[];temporal=[];contrasts=[];inputs=[];physical={};endpoints=[]
    for path in a.results:
        run=json.loads(path.read_text());assert run['status']=='completed'
        plan=run['plan'];source=plan['row'];inputs.append(dict(path=str(path),sha256=sha(path),plan=plan));static=None
        for result in run['results']:
            evidence=ROOT/result['evidence'];saved=result['report'];protocol=result['protocol'];model=result['model']
            assert saved['initial_states_sha256']==plan['states_sha256']
            if model!='static':assert saved['checkpoint_sha256']==plan['models'][model]['sha256']
            with np.load(evidence/'trace.npz') as archive:trace={key:archive[key] for key in archive.files}
            steps,n=trace['active'].shape;assert n==128 and 0<steps<=600
            alive=(trace['active']&~trace['fall']&~trace['invalid']).all(0)&(steps==600)
            body=alive&(trace['drift']<.01).all(0)&(trace['rotation']<.25).all(0)
            physical[result['evidence']]=n
            if protocol=='static':
                assert saved['alive_full']==int(alive.sum())
                static=dict(alive=alive,body=body)
                summaries.append(dict(source=source,model='static',protocol='static',n=n,success=None,alive=int(alive.sum()),body_stable=int(body.sum())))
                continue
            assert static is not None
            if protocol=='arrival':
                rescored=score_arrival_trace(trace,600,.01);metric='three_cycles'
            else:
                stage=150 if protocol=='fixed5' else 60
                rescored=score_timed_trace(trace,stage,9,600);metric='stable_full_all_endpoints'
                endpoints.extend(dict(source=source,model=model,protocol=protocol,**item) for item in grouped(stages(trace,stage)))
                for i,item in enumerate(summarize(trace,stage)):
                    assert item['strict']==rescored['records'][i][metric]
                    temporal.append(dict(source=source,model=model,protocol=protocol,**item))
            for key,value in rescored.items():assert saved[key]==value,(source,model,protocol,key)
            for i,record in enumerate(rescored['records']):
                trials.append(dict(source=source,model=model,protocol=protocol,trial=i,success=record[metric],
                    alive=record['alive_full'],body_stable=bool(body[i]),static_alive=bool(static['alive'][i]),static_stable=bool(static['body'][i]),
                    first_cycle=record['first_cycle'],cycles=record['cycles'] if protocol=='arrival' else sum(all(record['endpoints_held'][j:j+2]) for j in range(0,len(record['endpoints_held']),2)),
                    max_drift_mm=record['max_drift_m']*1000,max_rotation_deg=float(np.rad2deg(record['max_rotation_rad'])),
                    checkpoint_sha256=saved['checkpoint_sha256']))
            selected=trials[-n:]
            summaries.append(dict(source=source,model=model,protocol=protocol,n=n,success=sum(row['success'] for row in selected),
                alive=sum(row['alive'] for row in selected),body_stable=int(body.sum()),first_cycle=sum(row['first_cycle'] for row in selected),
                static_stable_n=int(static['body'].sum()),success_on_static_stable=sum(row['success'] and row['static_stable'] for row in selected),
                trace_sha256=sha(evidence/'trace.npz'),reused=result.get('reused_identical_checkpoint_evidence',False)))
        for suffix in ('final','selected'):
            for protocol in ('fixed2','fixed5','arrival'):
                original=[row for row in trials if row['source']==source and row['model']=='original-'+suffix and row['protocol']==protocol]
                changed=[row for row in trials if row['source']==source and row['model']=='dense1-'+suffix and row['protocol']==protocol]
                assert len(original)==len(changed)==128
                contrasts.append(dict(source=source,selection=suffix,protocol=protocol,
                    changed_minus_original_pp=100*sum(int(b['success'])-int(x['success']) for x,b in zip(original,changed))/128,
                    changed_only=sum(b['success'] and not x['success'] for x,b in zip(original,changed)),
                    original_only=sum(x['success'] and not b['success'] for x,b in zip(original,changed)),
                    both=sum(x['success'] and b['success'] for x,b in zip(original,changed))))
    with (a.output/'trials.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(trials[0]),lineterminator='\n');writer.writeheader();writer.writerows(trials)
    (a.output/'temporal-diagnostics.json').write_text(json.dumps(temporal,indent=2)+'\n')
    (a.output/'endpoint-diagnostics.json').write_text(json.dumps(endpoints,indent=2)+'\n')
    result=dict(status='independently_rescored',inputs=inputs,summaries=summaries,contrasts=contrasts,
        unique_physical_episodes_including_static=sum(physical.values()),reported_policy_rows=len(trials),
        scope='Within-source128 perturbation paired empirical differences, one continuation seed unless separately replicated. Two distinct sources, not256 independent base grasps. Identical final/selected weight evidence explicitly reused; not new physical trials. No hardware or novel-grasp-generalization claim.')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],summaries=summaries,contrasts=contrasts),indent=2))


if __name__=='__main__':main()
