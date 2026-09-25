"""Rescore physical outcomes and quantify estimator error before/after feedback diverges."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace

SCALES = np.array([.001, .001, .001, .02, .02, .02, .0005, .01])


def analyze(folder):
    report = json.loads((folder/'report.json').read_text())
    audit = json.loads((folder/'state-estimation-audit.json').read_text())
    assert audit['status'] == 'passed'
    assert audit['teacher_unchanged'] and audit['encoder_unchanged']
    assert not audit['current_privileged_actor_input']
    checks = audit['checks']
    count = report['num_envs'] * report['recorded_steps']
    assert checks['physics_transitions'] == count
    assert checks['latest_history_matches'] == count
    assert checks['teacher_physics_transitions'] == 0
    assert checks['privileged_invariance'] >= report['num_envs']
    assert checks['changed_history_rows'] > 0
    with np.load(folder/'trace.npz') as z:
        trace = {k:z[k] for k in ['active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation']}
    rescored = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
    assert rescored['records'] == report['records']
    with np.load(folder/'estimation-trace.npz') as z:
        prediction, target, active = z['prediction'], z['target'], z['active']
    assert prediction.shape == target.shape == (600, report['num_envs'], 8)
    assert active.shape == prediction.shape[:2] and active.dtype == bool
    assert np.isfinite(prediction).all() and np.isfinite(target).all()
    error = (prediction.astype(np.float64)-target.astype(np.float64))*SCALES
    rmse = np.sqrt(np.mean(error[active]**2, axis=0))
    assert np.allclose(rmse, audit['rmse_physical'], atol=2e-7, rtol=2e-5)
    body = (np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) &
            (trace['drift'] < .01) & (trace['rotation'] < .25)).all(0)
    alive = np.array([r['alive_full'] for r in report['records']])
    body &= alive
    slices = [(0,1), (1,2), (2,3)] if report['num_envs'] == 3 else [(0,100), (100,200), (200,300), (300,332)]
    assert report['num_envs'] in (3,332)
    groups = []
    for lo,hi in slices:
        group_error = error[:,lo:hi][active[:,lo:hi]]
        records = report['records'][lo:hi]
        groups.append(dict(count=hi-lo, joint=sum(r['stable_full_all_endpoints'] for r in records),
            alive=int(alive[lo:hi].sum()), body=int(body[lo:hi].sum()),
            all_endpoints=sum(r['all_endpoints_held'] for r in records),
            active_transitions=len(group_error), rmse=np.sqrt(np.mean(group_error**2,axis=0)).tolist()))
    windows=[]
    for lo,hi in [(0,15),(15,60),(60,150),(150,600)]:
        e=error[lo:hi][active[lo:hi]]
        windows.append(dict(start_step=lo,end_step_exclusive=hi,active_transitions=len(e),
            rmse=np.sqrt(np.mean(e**2,axis=0)).tolist() if len(e) else None,
            slider_abs_error_quantiles_m=np.quantile(np.abs(e[:,6]),[.5,.9,.99]).tolist() if len(e) else None))
    return dict(folder=str(folder),policy_kind=report['policy_kind'],phase=audit['phase'],update=audit['update'],
        seconds=report['protocol']['stage_steps']/30,num_envs=report['num_envs'],
        actual_transitions=count,joint=report['stable_full_all_endpoints'],alive=report['alive_full'],
        body=int(body.sum()),groups=groups,rmse=rmse.tolist(),time_windows=windows,
        student_sha256=audit['student_sha256'],
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [folder/'report.json',folder/'trace.npz',folder/'estimation-trace.npz',folder/'state-estimation-audit.json']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folders',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.output.exists()
    rows=[analyze(folder) for folder in args.folders]
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        records_rescored_exact=True,history_and_action_counts_verified=True,rows=rows,
        scope='Frozen student-only physical evaluation. Reused development states, not independent validation or hardware. Estimation errors are pre-action; task trace is post-action. RMSE excludes inactive rows, so failures change its denominator.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(folder=r['folder'],joint=r['joint'],alive=r['alive'],
        slider_rmse_mm=1000*r['rmse'][6],groups=[g['joint'] for g in r['groups']]) for r in rows]))


if __name__=='__main__':
    main()
