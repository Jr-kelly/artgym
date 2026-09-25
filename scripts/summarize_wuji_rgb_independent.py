"""Report preregistered fresh-cohort reliability with paired uncertainty.

Consumes only a complete, independently rescored result. Three trained grasp
families have new unfiltered perturbations; the fourth is a reused failure
control. Neither a passed threshold nor a successful simulation establishes
unseen-grasp, camera, geometry or hardware transfer.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def wilson(success,total):
    z=1.959963984540054;p=success/total;den=1+z*z/total
    center=(p+z*z/(2*total))/den
    radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0.,center-radius),min(1.,center+radius)]


def rate(values):
    count=int(np.sum(values));total=len(values)
    return dict(success=count,trials=total,rate=count/total,wilson95=wilson(count,total))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--cohort',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1]
    audit=json.loads(args.audit.read_text());assert audit['status']=='verified_complete'
    assert audit['physics_transitions']==796800 and len(audit['audits'])==16
    manifest=json.loads((args.cohort/'manifest.json').read_text())
    assert manifest['created']>manifest['models_frozen']
    assert manifest['no_outcome_filter'] and manifest['physics_transitions']==0
    assert hashlib.sha256((args.cohort/'mixed332.npy').read_bytes()).hexdigest()==manifest['initial_states_sha256']
    assert audit['initial_states_sha256']==manifest['initial_states_sha256']
    assert audit['evaluation_seed']==manifest['seed']
    for model,candidate in manifest['candidates'].items():
        assert hashlib.sha256((root/candidate['path']).read_bytes()).hexdigest()==candidate['sha256']
        assert audit['artifacts'][model]['sha256']==candidate['sha256']
    assert manifest['splits']['fourth']['reused_development_failure_control']
    conditions={};vectors={};decisions={};paired={}
    for model in ['baseline','mixed']:
        decisions[model]=True
        for seconds in [2,5]:
            key=f'{model}-{seconds}s';source=audit['conditions'][key]
            records=source['records'];assert set(map(int,records))==set(range(332))
            values=np.array([records[str(i)]['stable_full_all_endpoints'] for i in range(332)],dtype=bool)
            vectors[key]=values
            groups=[rate(values[start:start+100]) for start in [0,100,200]]
            total=rate(values[:300]);passed=total['rate']>=.95 and all(g['rate']>=.90 for g in groups)
            decisions[model]&=passed
            conditions[key]=dict(fresh300=total,trained_grasp_groups=groups,
                reused_fourth32=rate(values[300:]),working_threshold_passed=passed,
                body_only=rate([records[str(i)]['body_only'] for i in range(300)]),
                all_endpoints=rate([records[str(i)]['all_endpoints_held'] for i in range(300)]))
    rng=np.random.default_rng(20261122)
    for seconds in [2,5]:
        base=vectors[f'baseline-{seconds}s'][:300];mixed=vectors[f'mixed-{seconds}s'][:300]
        delta=mixed.astype(int)-base.astype(int);samples=[]
        for _ in range(10000):
            indices=np.concatenate([start+rng.integers(0,100,100) for start in [0,100,200]])
            samples.append(float(delta[indices].mean()))
        paired[str(seconds)]=dict(mixed_minus_baseline_rate=float(delta.mean()),
            stratified_paired_bootstrap95=np.quantile(samples,[.025,.975]).tolist(),
            baseline_only=int(np.sum(base&~mixed)),mixed_only=int(np.sum(~base&mixed)),
            both_success=int(np.sum(base&mixed)),both_failure=int(np.sum(~base&~mixed)),
            bootstrap_seed=20261122,repeats=10000)
    # Jointly succeeding under both clocks is useful context, not an additional
    # criterion chosen after seeing outcomes. Preserve paired initial row IDs.
    both_clocks={model:rate(vectors[f'{model}-2s'][:300]&vectors[f'{model}-5s'][:300])
                 for model in ['baseline','mixed']}
    result=dict(status='complete',finished=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        conditions=conditions,passed_both_preregistered_clocks=decisions,paired_comparisons=paired,
        descriptive_both_clocks_same_state=both_clocks,acceptance=manifest['acceptance'],
        manifest_sha256=hashlib.sha256((args.cohort/'manifest.json').read_bytes()).hexdigest(),
        audit_sha256=hashlib.sha256(args.audit.read_bytes()).hexdigest(),model_hashes=manifest['candidates'],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope=__doc__)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(conditions=conditions,passed=decisions,paired=paired)))


if __name__=='__main__':main()
