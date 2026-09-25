"""Evaluate a frozen physical estimator on teacher histories at two command clocks.

This is an offline distribution diagnostic on reused development states. It is
not a closed-loop evaluation or an independent generalization claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common  # IsaacGym before torch.
import numpy as np
import torch
from scripts.wuji_physical_state_encoder import make_encoder
from scripts.audit_distillation_runtime import tensor_digest
from scripts.wuji_timed_command_metrics import score_timed_trace


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--datasets', type=Path, nargs=2, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    torch.set_num_threads(4)
    artifact = torch.load(args.artifact, map_location='cpu')
    assert digest(args.artifact) == json.loads(args.artifact.with_suffix('.json').read_text())['sha256']
    encoder, _ = make_encoder(artifact['encoder_spec'])
    encoder.load_state_dict(artifact['state_encoder'])
    encoder.eval()
    before = tensor_digest(encoder.state_dict())
    scale = torch.tensor(artifact['output_scales'])
    result = dict(scope=__doc__, artifact_sha256=digest(args.artifact), datasets=[])
    saved_rows = None
    for dataset in args.datasets:
        manifest = json.loads(dataset.with_name('dataset-manifest.json').read_text())
        assert manifest['status'] == 'passed' and digest(dataset) == manifest['dataset_sha256']
        assert manifest['source_teacher_sha256'] == artifact['teacher_sha256']
        report = json.loads(dataset.with_name('report.json').read_text())
        with np.load(dataset.with_name('trace.npz')) as z:
            trace = {k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
        rescored = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
        assert rescored['records'] == report['records']
        with np.load(dataset) as z:
            history, target, active = z['history'], z['target'], z['active']
            rows, training, steps = z['initial_rows'], z['train_rows'], z['step']
        assert history.shape == (150,90,2055) and target.shape == (150,90,8)
        assert np.array_equal(steps, np.arange(0,600,4))
        assert np.array_equal(training, rows%100 < 20)
        assert len(set(rows[training]) & set(rows[~training])) == 0
        if saved_rows is not None:
            assert np.array_equal(saved_rows, rows)
        saved_rows = rows
        predictions = []
        with torch.no_grad():
            flat = torch.from_numpy(history.reshape(-1,2055))
            for start in range(0,len(flat),256):
                predictions.append((encoder(flat[start:start+256])*scale).numpy())
        prediction = np.concatenate(predictions).reshape(target.shape)
        error = prediction.astype(np.float64)-target
        assert np.isfinite(error).all()
        groups = []
        stage_steps = report['protocol']['stage_steps']
        late = np.broadcast_to((steps%stage_steps >= stage_steps-9)[:,None],active.shape)
        for split, split_mask in [('train',training),('validation',~training)]:
            for grasp in [None,0,1,2]:
                base = active & split_mask[None,:]
                if grasp is not None:
                    base &= (rows//100 == grasp)[None,:]
                for phase, mask in [('all',base),('late',base & late),
                                    ('open',base & (target[...,6]>.03)),
                                    ('closed',base & (target[...,6]<.005))]:
                    if not mask.any():
                        continue
                    e=error[mask]
                    groups.append(dict(split=split,grasp=grasp,phase=phase,count=int(mask.sum()),
                        rmse=np.sqrt(np.mean(e*e,axis=0)).tolist(),
                        bias=e.mean(0).tolist(),abs_p95=np.percentile(abs(e),95,axis=0).tolist()))
        result['datasets'].append(dict(dataset=str(dataset),dataset_sha256=digest(dataset),
            seconds=report['protocol']['stage_seconds'],groups=groups,
            physics_records_rescored_exact=True,teacher_joint=report['stable_full_all_endpoints'],
            train_count=int((active & training[None,:]).sum()),
            validation_count=int((active & ~training[None,:]).sum())))
    assert tensor_digest(encoder.state_dict()) == before
    result['encoder_unchanged'] = True
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for data in result['datasets']:
        print(json.dumps(dict(seconds=data['seconds'],teacher_joint=data['teacher_joint'],
            groups=[g for g in data['groups'] if g['split']=='validation' and g['grasp'] is None])))


if __name__ == '__main__':
    main()
