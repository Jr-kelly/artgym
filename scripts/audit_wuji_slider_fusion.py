"""Verify frozen slider fits against original recorded histories and data splits."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_slider_fusion import SliderFusionEncoder,features,predict_residual
from scripts.wuji_physical_state_encoder import make_encoder,SCALES
from scripts.wuji_kinematics import WujiKinematics
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();torch.set_num_threads(4)
    data=ROOT/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data';manifest=json.loads((data/'manifest.json').read_text())
    with np.load(data/'memory-features.npz') as z:
        sensor=z['features'][:,::4].astype(np.float64);target=z['target'][...,6]/SCALES[6]
        training=z['train_rows'];rows=z['initial_rows']
    assert np.array_equal(training,rows%100<20) and len(np.unique(rows))==90
    initial=ROOT/'runs/wuji-goal/diagnostics/state-scale-2036-v1/artifacts/precision_units.pth'
    original=torch.load(initial,map_location='cpu');ratio=torch.tensor(original['output_scales'])/torch.tensor(SCALES)
    kin=WujiKinematics();results={}
    for arm in ['raw','kinematic']:
        path=ROOT/f'runs/wuji-goal/diagnostics/slider-fusion-2254-v1/fitting/{arm}.pth'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==json.loads(path.with_suffix('.json').read_text())['sha256']
        artifact=torch.load(path,map_location='cpu');f=artifact['slider_fusion']
        assert tensor_digest(original['state_encoder'])==tensor_digest(artifact['state_encoder'])
        x=features(sensor,kin,arm);train=x[:,:,training].reshape(-1,x.shape[-1])
        assert np.array_equal(f['mean'],train.mean(0)) and np.array_equal(f['scale'],np.maximum(train.std(0),1e-3))
        design=np.column_stack([np.clip((train-f['mean'])/f['scale'],-10,10),np.ones(len(train))])
        y=(target-sensor[...,101])[:,:,training].reshape(-1)
        weights=np.r_[f['weight'],f['bias']]
        gradient=design.T@(design@weights-y)/len(train)+.01*np.r_[weights[:-1],0.]
        # Stored labels originate in float32; evaluate the normal equations with
        # the same SI conversion used by fitting, rather than rounded targets.
        with np.load(data/'memory-features.npz') as z:
            exact_y=(z['target'][...,6].astype(np.float64)/SCALES[6]-sensor[...,101])[:,:,training].reshape(-1)
        gradient=design.T@(design@weights-exact_y)/len(train)+.01*np.r_[weights[:-1],0.]
        assert np.abs(gradient).max()<1e-10
        core,_=make_encoder(artifact['encoder_spec']);core.load_state_dict(artifact['state_encoder']);core.eval()
        model=SliderFusionEncoder(core,artifact).eval();before=tensor_digest(model.state_dict())
        maxima=[]
        with torch.no_grad():
            for s,source in enumerate(manifest['sources']):
                source_path=ROOT/'runs'/source['path'].split('/runs/',1)[1]
                assert hashlib.sha256(source_path.read_bytes()).hexdigest()==source['sha256']
                with np.load(source_path) as z:history=z['history'][[0,31,79,149]][:,[0,25,40,55,70,85]].reshape(-1,2055)
                inp=torch.from_numpy(history);base=core(inp);actual=model(inp)*ratio
                cached=sensor[s][[0,31,79,149]][:,[0,25,40,55,70,85]].reshape(-1,103)
                expected=cached[:,95:103].copy()
                expected[:,6]+=predict_residual(features(cached,kin,arm),f['mean'],f['scale'],f['weight'],f['bias'])
                errors=np.abs((actual.numpy()-expected)*np.array(SCALES)).max(0)
                assert np.all(errors<np.array([5e-5]*3+[1e-3]*3+[5e-5,1e-3])),errors
                assert torch.equal(actual[:,:6],(base*ratio)[:,:6]) and torch.equal(actual[:,7],(base*ratio)[:,7])
                maxima.append(errors.tolist())
            # A zero residual must recover the original network bit for bit.
            saved_weight=model.weight.clone();saved_bias=model.bias.clone();model.weight.zero_();model.bias.zero_()
            assert torch.equal(model(inp),core(inp));model.weight.copy_(saved_weight);model.bias.copy_(saved_bias)
        assert tensor_digest(model.state_dict())==before
        results[arm]=dict(status='passed',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            normalizer_training_only=True,normal_equation_max_error=float(np.abs(gradient).max()),
            original_history_checks=96,backend_max_physical_error=np.max(maxima,axis=0).tolist(),
            body_velocity_unchanged=True,zero_residual_exact=True,weights_unchanged=True)
    atomic_json(args.output,dict(status='passed',created=now(),arms=results,scope=__doc__,
        physics_runtime_gates='Separate required tests compare current FK against simulator, truth mutation and actual executed actions.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print(json.dumps(results))


if __name__=='__main__':main()
