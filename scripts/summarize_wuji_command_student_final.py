"""Rescore all frozen command-policy conditions from saved physical traces."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-partial',action='store_true');p.add_argument('--expected-conditions',type=int,default=12)
    args=p.parse_args()
    assert not args.output.exists()
    status=json.loads((args.run/'status.json').read_text())
    if not args.allow_partial:assert status['status']=='completed'
    rows=[]
    for path in sorted(args.run.glob('formal-*/report.json')):
        d=json.loads(path.read_text());folder=path.parent
        a=json.loads((folder/'command-student-audit.json').read_text())
        assert a['status']=='passed' and a['model_unchanged'] and not a['current_object_input']
        assert a['checks']['teacher_action_calls']==0
        assert a['checks']['physics_transitions']==332*600
        with np.load(folder/'trace.npz') as z:
            trace={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
        score=score_timed_trace(trace,d['protocol']['stage_steps'],9,600)
        assert score['records']==d['records']
        # stable_full also requires a first successful command pair. Body-only
        # stability must be scored independently to diagnose grasp failures.
        body_ok=np.all(trace['active'].astype(bool) & ~trace['fall'].astype(bool)
            & ~trace['invalid'].astype(bool) & np.isfinite(trace['drift'])
            & np.isfinite(trace['rotation']) & (trace['drift']<.01)
            & (trace['rotation']<.25),axis=0)
        groups=[]
        for start,end in [(0,100),(100,200),(200,300),(300,332)]:
            records=d['records'][start:end]
            groups.append(dict(count=end-start,joint=sum(v['stable_full_all_endpoints'] for v in records),
                alive=sum(v['alive_full'] for v in records),body=int(body_ok[start:end].sum()),
                body_and_first_cycle=sum(v['stable_full'] for v in records),
                endpoints=sum(v['all_endpoints_held'] for v in records)))
        rows.append(dict(name=folder.name,arm=a['arm'],update=a['update'],seconds=d['protocol']['stage_seconds'],
            joint=sum(g['joint'] for g in groups[:3]),body=sum(g['body'] for g in groups[:3]),
            endpoints=sum(g['endpoints'] for g in groups[:3]),alive=sum(g['alive'] for g in groups[:3]),
            groups=groups,checks=a['checks'],model_sha256=a['artifact_sha256'],
            source_sha256={f:hashlib.sha256((folder/f).read_bytes()).hexdigest() for f in ['report.json','trace.npz','command-student-audit.json']}))
    if not args.allow_partial:assert len(rows)==args.expected_conditions
    assert len({(r['update'],r['seconds']) for r in rows})==len(rows)
    args.output.write_text(json.dumps(dict(status='verified_partial' if args.allow_partial else 'verified',
        conditions_rescored=len(rows),expected_conditions=args.expected_conditions,physics_transitions=len(rows)*332*600,
        rows=rows,scope='3traininggrasps x100perturbations plusfourth32, reuseddevelopmentstates. Allcommandsheld2mm andbody10mm/.25rad. Noindependentorhardwaresuccess.'),indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['arm','update','seconds','joint','body','endpoints','alive','groups']} for r in rows]))


if __name__=='__main__':
    main()
