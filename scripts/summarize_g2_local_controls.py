"""Machine-readable completed baseline/control diagnostics, not training metrics."""
import argparse
import csv
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('runs/g2-local-policy-20260928'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();rows=[]
    def local(name,task,episodes):
        for episode,m in enumerate(episodes):
            for replica,complete in enumerate(m['complete']):
                prep=m.get('preparation',{}).get('preparation_pass',[True]*len(m['complete']))[replica]
                rows.append(dict(run=name,scope='local reset; one acquired source',task=task,episode=episode,replica=replica,
                    complete=complete,local_success=m['success'][replica] and prep,continuous_success=False,
                    world_stable=m['stable'][replica],endpoint_10mm=m['endpoints_10mm'][replica] and complete,
                    endpoint_2mm=m['endpoints_2mm'][replica] and complete,world_drift_mm=m['world_drift_m'][replica]*1000,
                    world_rotation_rad=m['world_rotation_rad'][replica],slider_travel_mm=m['slider_travel_m'][replica]*1000,
                    endpoints_mm=json.dumps([v*1000 for v in m['endpoint_max_errors_m'][replica]]) if task=='S' else None,
                    first_instability_s=m['first_instability_s'][replica],drop=m['drop'][replica],
                    failure=('preparation_failed' if not prep else 'world_instability' if not m['stable'][replica] else 'endpoint_failure' if not m['endpoints_10mm'][replica] else None),
                    raw=str(a.root/name/('episode-%03d.npz'%episode))))
    d=json.loads((a.root/'R1-01-local-fixed-H.json').read_text());local('R1-01','H',[d]);rows[-1]['raw']=str(a.root/'R1-01-local-fixed-H.npz')
    for folder in sorted(a.root.glob('R*-*')):
        if not folder.is_dir():continue
        report=folder/'report.json'
        if report.exists():
            d=json.loads(report.read_text())
            if 'episodes' in d:local(folder.name,d['args']['task'],d['episodes'])
            elif (folder/'learned-hold.json').exists():
                h=json.loads((folder/'learned-hold.json').read_text())
                rows.append(dict(run=folder.name,scope='continuous table acquisition through H; Snotrequested',task='H',episode=0,replica=0,
                    complete=True,local_success=None,continuous_success=False,world_stable=h['stable_10mm_025rad'],
                    world_drift_mm=h['max_world_drift_m']*1000,world_rotation_rad=h['max_world_rotation_rad'],
                    failure='operation_not_requested',raw=str(folder/'trace.npz')))
            else:
                rows.append(dict(run=folder.name,scope='continuous table acquisition and operation',task='S',episode=0,replica=0,
                    complete=d.get('operation_steps')==600,local_success=None,
                    continuous_success=d.get('whole_stable_success',False) and d.get('operation_steps')==600,
                    world_stable=d.get('stable_world_10mm_025rad'),endpoint_10mm=d.get('basic_10mm'),endpoint_2mm=d.get('strict_2mm'),
                    world_drift_mm=d.get('world_drift_max_m',0)*1000,world_rotation_rad=d.get('world_rotation_max_rad'),
                    slider_travel_mm=d.get('slider_travel_m',0)*1000,endpoints_mm=json.dumps([e['max_error_m']*1000 for e in d.get('endpoints',[])]),
                    failure=d.get('failure_class'),raw=str(folder/'trace.npz')))
        elif (folder/'failure.json').exists():
            d=json.loads((folder/'failure.json').read_text());rows.append(dict(run=folder.name,scope='continuous acquisition aborted',task='H',episode=0,replica=0,
                complete=False,local_success=False,continuous_success=False,failure='measurement_gate_missing_before_learner: '+d['message'],raw=str(folder/'partial-trace.npz')))
    for episode in [0,1]:
        for replica in [0,1]:
            rows.append(dict(run='R1-03-parallel-repeat-H',scope='coordinate-bug diagnostic',task='H',episode=episode,replica=replica,
                complete=episode==0,local_success=False,continuous_success=False,
                failure='invalid environment-origin conversion' if episode==0 else 'interrupted after origin bug found; raw incomplete',
                raw=str(a.root/'R1-03-parallel-repeat-H/episode-000.npz') if episode==0 else None))
    rows.sort(key=lambda r:(r['run'],r['episode'],r['replica']))
    fields=sorted(set(k for row in rows for k in row))
    with a.output.open('w',newline='') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(output=str(a.output),completed_or_preserved_control_attempts=len(rows))))


if __name__=='__main__':main()
