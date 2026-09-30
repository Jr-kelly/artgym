"""Summarize frozen train probes and held-out physical/action error by source/phase."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--pairs',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
    for pair in a.pairs:
        assert any((pair/arm/'manifest.json').exists() for arm in ['M','E'])
        for arm in ['M','E']:
            if not (pair/arm).exists():continue  # Explicit later single-arm continuation.
            path=pair/arm;manifest=json.loads((path/'manifest.json').read_text())
            for line in (path/'metrics.jsonl').read_text().splitlines():
                item=json.loads(line)
                for split in ['validation','training_probe']:
                    for i,m in enumerate(item[split]):
                        data=Path(manifest['data'][i]['path']);source=int(data.name[-1]);seconds=int(data.parent.name[-1])
                        row=dict(pair=pair.name,arm=arm,epoch=item['epoch'],updates=item['updates'],split=split,source=source,seconds=seconds,**{k:v for k,v in m.items() if k!='phase_metrics'})
                        phases=[]
                        for phase in range(6):
                            part=[x for x in m['phase_metrics'] if x['phase']==phase];n=sum(x['n'] for x in part)
                            if n:phases.append(dict(phase=phase,n=n,**{key:sum(x[key]*x['n'] for x in part)/n for key in ['raw_mse','executed_mse','thumb_target_rad','support_target_rad']}))
                        row['phases']=phases;rows.append(row)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(dict(rows=rows,phase_names=['open_moving','open_arrival_1_to_9','open_holding_after9','close_moving','close_arrival_1_to_9','close_holding_after9'],scope='Offline recorded-history errors; training_probe uses first8 fitting trajectories; actual changing-model training batches retained separately in training.jsonl'),indent=2)+'\n')
    for arm in ['M','E']:
        selected=[r for r in rows if r['arm']==arm and r['split']=='validation'];epochs=sorted(set(r['epoch'] for r in selected))
        for epoch in epochs:
            group=[r for r in selected if r['epoch']==epoch];print(json.dumps(dict(arm=arm,epoch=epoch,executed_mse=sum(r['executed_action_mse'] for r in group)/len(group),target_range_mean=sum(r['target_range_mean'] for r in group)/len(group),source3_target_mean=sum(r['target_range_mean'] for r in group if r['source']==3)/sum(r['source']==3 for r in group))))
if __name__=='__main__':main()
