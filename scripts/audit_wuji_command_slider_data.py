"""Independent alignment/normalization and input-masking checks for command data."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_command_slider import CommandSliderResidual
from scripts.wuji_kinematics import WujiKinematics
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();folder=ROOT/'runs/wuji-goal/diagnostics/command-slider-2323-v1/data'
    meta=json.loads((folder/'manifest.json').read_text());data=folder/'command-features.npz'
    assert hashlib.sha256(data.read_bytes()).hexdigest()==meta['dataset_sha256']
    with np.load(data) as z:
        x=z['features'];y=z['target'];base=z['base_prediction'];rows=z['initial_rows'];training=z['train_rows'];steps=z['label_steps'];mean=z['feature_mean'];scale=z['feature_scale']
    with np.load(ROOT/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data/memory-features.npz') as z:
        assert np.array_equal(x[...,:103],z['features'][:,steps])
        assert np.array_equal(y,z['target']) and np.array_equal(base,z['base_prediction'][:,steps])
    train=x[:,:,training].reshape(-1,148).astype(np.float64)
    assert np.array_equal(mean,train.mean(0).astype(np.float32))
    assert np.array_equal(scale,np.maximum(train.std(0),1e-3).astype(np.float32))
    assert np.array_equal(training,rows%100<20) and len(train)==36000
    kin=WujiKinematics();states=np.load(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy');aligned=[]
    for i,source in enumerate(meta['sources']):
        path=ROOT/source['trace'];assert hashlib.sha256(path.read_bytes()).hexdigest()==source['trace_sha256']
        with np.load(path) as z:
            targets=z['target'][:,rows];past_actions=z['action'][steps[1:]-1][:,rows]
        desired=np.concatenate([states[rows,20:40][None],targets[steps[1:]-1]],axis=0).astype(np.float64)
        normalized=(2*(desired-kin.lower)/(kin.upper-kin.lower)-1).astype(np.float32)
        assert np.array_equal(normalized,x[i,...,128:])
        assert np.array_equal(past_actions,x[i,1:,:,20:40]);aligned.append(source['key'])
    torch.manual_seed(20261078);net=CommandSliderResidual(mean,scale)
    with torch.no_grad():
        # Give the diagnostic copy a nonzero head to exercise actual dependency.
        torch.nn.init.normal_(net.net[-1].weight,std=.1)
        test=torch.from_numpy(x.reshape(-1,148)[::503].copy())
        changed=test.clone();changed[:,128:]+=.1
        assert torch.equal(net(test,'masked'),net(changed,'masked'))
        changed_count=int((net(test,'provided')!=net(changed,'provided')).sum());assert changed_count>0
        net.zero_grad(set_to_none=True)
    current=test.clone().requires_grad_(True);net(current,'masked').sum().backward()
    assert torch.count_nonzero(current.grad[:,128:])==0
    result=dict(status='passed',created=now(),dataset_sha256=meta['dataset_sha256'],sources_aligned=aligned,
        all_labels_equal_original=True,own_target_alignment_exact=True,normalizer_training_only=True,
        training_samples=36000,validation_samples=18000,masked_target_invariance=True,
        masked_target_gradient_exact_zero=True,provided_changed_examples=changed_count,
        diagnostic_weights_only=True,no_training_physics=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    atomic_json(args.output,result);print(json.dumps(result))


if __name__=='__main__':main()
