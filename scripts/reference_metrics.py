"""Section 4.1 metrics with equal instance weighting for coverage and CSC."""
import numpy as np


def aggregate_reference_metrics(instances):
    rows=[]
    for name,data in instances.items():
        cycles=np.asarray(data['consecutive_success_cycles_trials'],dtype=float)
        if cycles.ndim!=2 or not cycles.size or not np.isfinite(cycles).all():
            raise ValueError(f'Invalid trial matrix for {name}')
        successful=cycles.max(axis=0)>=1
        rows.append(dict(instance=name,instance_coverage=float(successful.any()),
            grasp_coverage=float(successful.mean()),
            csc_mean=float(cycles.mean(axis=0)[successful].mean()) if successful.any() else 0.,
            csc_max=float(cycles[:,successful].max()) if successful.any() else 0.,
            successful_trials=int((cycles>=1).sum()),trials=int(cycles.size)))
    if not rows:raise ValueError('No evaluated instances')
    metrics={key:float(np.mean([row[key] for row in rows])) for key in
        ('instance_coverage','grasp_coverage','csc_mean','csc_max')}
    metrics.update(execution_success_rate=sum(r['successful_trials'] for r in rows)/sum(r['trials'] for r in rows),
        per_instance=rows,empty_successful_subset_convention='CSC=0 for failed instances')
    return metrics


def unique_grasp_indices(states,dof,pos_threshold=.005,rot_threshold=.05,joint_rms_threshold=.0872664626):
    """Pose thresholds from upstream; 5-degree joint RMS is a declared assumption."""
    states=np.asarray(states)
    positions=states[:,2*dof:2*dof+3]
    quats=states[:,2*dof+3:2*dof+7].copy()
    quats/=np.maximum(np.linalg.norm(quats,axis=1,keepdims=True),1e-12)
    kept=[]
    for i in range(len(states)):
        if kept:
            pos=np.linalg.norm(positions[kept]-positions[i],axis=1)
            rot=2*np.arccos(np.clip(np.abs(quats[kept]@quats[i]),0,1))
            joint=np.sqrt(np.mean((states[kept,:dof]-states[i,:dof])**2,axis=1))
            if np.any((pos<=pos_threshold)&(rot<=rot_threshold)&(joint<=joint_rms_threshold)):continue
        kept.append(i)
    return np.asarray(kept,dtype=np.int64)
