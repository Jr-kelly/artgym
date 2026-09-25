"""Rescore equal-frame teachers; separate episode precision from grasp variation."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();assert not args.output.exists()
    rows=[];matrices={}
    for arm in ['upstream','corrected']:
        result=json.loads((args.run/arm/'result.json').read_text());assert result['status']=='completed'
        groups=[];per_grasp=[];matrices[arm]={}
        for name in ['030','031','032','033','034']:
            path=args.run/arm/(name+'.json');d=json.loads(path.read_text())
            cycles=np.asarray(d['consecutive_success_cycles_trials'])
            assert cycles.shape==(100,d['num_grasps']) and np.isfinite(cycles).all()
            assert np.equal(cycles,cycles.astype(int)).all() and (cycles>=0).all()
            success=cycles>=1;n=cycles.size;s=int(success.sum())
            assert s==d['successful_trials'] and n==d['total_trials']
            rates=success.mean(0);per_grasp.extend(rates.tolist());matrices[arm][name]=rates
            # Selection uses the first 50 trials; report performance on the
            # other 50 separately. This is a development diagnostic, not a
            # new-geometry or untouched blind experiment.
            selected=np.argsort(-success[:50].mean(0),kind='stable')[:5]
            top5=dict(selected_columns=selected.tolist(),selection_trials=[0,50],evaluation_trials=[50,100],
                selection_success=int(success[:50,selected].sum()),test_success=int(success[50:,selected].sum()),
                test_total=int(success[50:,selected].size),all_grasps_test_success=int(success[50:].sum()),
                all_grasps_test_total=int(success[50:].size))
            groups.append(dict(instance=name,success=s,total=n,num_grasps=d['num_grasps'],mean_cycles=float(cycles.mean()),top5_split_trial=top5,
                per_grasp_rates=rates.tolist(),report_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        total=sum(g['total'] for g in groups);success=sum(g['success'] for g in groups)
        assert total==result['total']==28700 and success==result['success']
        rows.append(dict(arm=arm,epoch=3400,frames=1088000000,success=success,total=total,rate=success/total,
            top5_split_trial_success=sum(g['top5_split_trial']['test_success'] for g in groups),
            top5_split_trial_total=sum(g['top5_split_trial']['test_total'] for g in groups),
            checkpoint_sha256=result['checkpoint_sha256'],groups=groups))
    difference=rows[1]['rate']-rows[0]['rate']
    # Paired grasp bootstrap, stratified by the five observed geometries.
    # This is not a confidence interval over future training seeds/geometries.
    rng=np.random.default_rng(20261086);draws=[]
    for _ in range(10000):
        pieces=[]
        for name in ['030','031','032','033','034']:
            a=matrices['upstream'][name];b=matrices['corrected'][name]
            ids=rng.integers(0,len(a),len(a));pieces.append((b-a)[ids])
        draws.append(float(np.concatenate(pieces).mean()))
    ci=np.quantile(draws,[.025,.975]).tolist()
    output=dict(status='verified',all10_cycle_matrices_rescored=True,rows=rows,
        corrected_minus_upstream=difference,paired_grasp_bootstrap95=ci,bootstrap_samples=10000,
        uncertainty_scope='Paired grasp bootstrap stratified by five observed geometries. Singletrainingseed/recovery histories; no general causal claim or confidence interval across newgeometries.',
        scope='Both frozen privileged teachers at1.088Bframes. 287seenheldoutgrasps x100newrandomized40s trials;10mm at-least-one-full-cycle criterion;notfinal2B andnotWuji2mmtimed metric.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(dict(rows=[{k:r[k] for k in ['arm','success','total','rate']} for r in rows],difference=difference,paired_grasp_bootstrap95=ci)))


if __name__=='__main__':main()
