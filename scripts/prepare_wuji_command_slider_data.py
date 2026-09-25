"""Add only previously issued joint targets to existing causal state data."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
from scripts.wuji_command_slider import command_features
from scripts.wuji_kinematics import WujiKinematics
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    source=ROOT/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data'
    manifest=json.loads((source/'manifest.json').read_text());dataset=source/'memory-features.npz'
    assert digest(dataset)==manifest['dataset_sha256']
    with np.load(dataset) as z:
        sensor=z['features'][:,z['label_steps']].astype(np.float64);target=z['target']
        steps=z['label_steps'];training=z['train_rows'];rows=z['initial_rows'];assert z['active'].all()
    assert np.array_equal(training,rows%100<20)
    states=ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'
    initial_targets=np.load(states)[rows,20:40];kin=WujiKinematics()
    data=[];provenance=[]
    for i,item in enumerate(manifest['sources']):
        pair=ROOT/'runs'/item['path'].split('/runs/',1)[1];assert digest(pair)==item['sha256']
        trace=pair.with_name('trace.npz')
        with np.load(trace) as z:targets=z['target'][:,rows];actions=z['action'][:,rows]
        # Targets in trace[t] are issued by action[t]; history at control step t
        # sees target[t-1]. Include the known acquisition command at step0.
        causal=np.concatenate([initial_targets[None],targets[:599]],axis=0)
        assert np.array_equal(sensor[i,1:,:,20:40].astype(actions.dtype),actions[steps[1:]-1])
        value=command_features(sensor[i],causal[steps].astype(np.float64),kin)
        assert value.shape==(150,90,148)
        data.append(value.astype(np.float32))
        provenance.append(dict(key=item['key'],trace=str(trace.relative_to(ROOT)),trace_sha256=digest(trace),
            original_pair_sha256=item['sha256'],target_alignment='target[t-1], initial known target at t=0',no_future_actions=True))
    features=np.stack(data);values=features[:,:,training].reshape(-1,148).astype(np.float64)
    mean=values.mean(0).astype(np.float32);scale=np.maximum(values.std(0),1e-3).astype(np.float32)
    out=args.output/'command-features.npz'
    np.savez_compressed(out,features=features,target=target,base_prediction=sensor[...,95:103].astype(np.float32),
        initial_rows=rows,train_rows=training,label_steps=steps,feature_mean=mean,feature_scale=scale)
    result=dict(status='completed',created=now(),dataset_sha256=digest(out),sources=provenance,
        original_dataset_sha256=digest(dataset),initial_sha256=manifest['initial_sha256'],teacher_sha256=manifest['teacher_sha256'],
        initial_states_sha256=digest(states),shape=list(features.shape),training_rows=rows[training].tolist(),
        validation_rows=rows[~training].tolist(),normalizer_training_only=True,no_new_physics=True,
        additional_input='20 previously issued commanded targets. Runtime owns these registers; no current object/contact truth.',
        source_sha256=digest(Path(__file__)))
    atomic_json(args.output/'manifest.json',result);print(json.dumps(result))


if __name__=='__main__':main()
