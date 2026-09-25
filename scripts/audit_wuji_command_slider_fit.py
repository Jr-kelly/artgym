"""Check paired command-input initialization, optimizer steps and frozen tensors."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.audit_distillation_runtime import tensor_digest
from scripts.wuji_command_slider import CommandSliderResidual
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==json.loads(path.with_suffix('.json').read_text())['sha256']
    return torch.load(path,map_location='cpu')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();torch.set_num_threads(4)
    original=torch.load(ROOT/'runs/wuji-goal/diagnostics/state-scale-2036-v1/artifacts/precision_units.pth',map_location='cpu')
    base=tensor_digest(original['state_encoder']);records={};initial_digests=[]
    with np.load(args.run/'data/command-features.npz') as z:x=torch.from_numpy(z['features'][0,:2,:3].copy())
    for folder,budget in [('preflight',2),('fitting',1000)]:
        status=args.run/folder/'status.json'
        if not status.exists():continue
        state=json.loads(status.read_text());assert state['status']=='completed' and state['updates_completed']==budget
        assert state['samples_each']==budget*512
        arms={}
        for arm in ['provided','masked']:
            start=load(args.run/folder/f'{arm}-update0000.pth');end=load(args.run/folder/f'{arm}-update{budget:04d}.pth')
            initial_digests.append(tensor_digest(start['command_encoder']))
            assert tensor_digest(start['state_encoder'])==tensor_digest(end['state_encoder'])==base
            assert np.array_equal(start['command_mean'],end['command_mean']) and np.array_equal(start['command_scale'],end['command_scale'])
            for v in end['command_optimizer']['state'].values():assert int(v['step'])==budget
            assert start['command_optimizer']['state']=={}
            net=CommandSliderResidual(end['command_mean'],end['command_scale']);net.load_state_dict(end['command_encoder']);net.eval()
            changed=x.clone();changed[...,128:]+=.1
            with torch.no_grad():
                prediction=net(x,arm);altered=net(changed,arm)
                count=int((prediction!=altered).sum())
            weights_unchanged=torch.equal(start['command_encoder']['net.0.weight'][:,128:],end['command_encoder']['net.0.weight'][:,128:])
            if arm=='masked':assert count==0 and weights_unchanged
            else:assert count>0 and not weights_unchanged
            assert torch.count_nonzero(start['command_encoder']['net.4.weight'])==0
            assert torch.count_nonzero(start['command_encoder']['net.4.bias'])==0
            arms[arm]=dict(optimizer_steps=budget,base_frozen=True,normalizer_frozen=True,
                input_target_weights_unchanged=weights_unchanged,changed_target_changes_predictions=count,
                final_sha256=hashlib.sha256((args.run/folder/f'{arm}-update{budget:04d}.pth').read_bytes()).hexdigest())
        records[folder]=arms
    assert records and len(set(initial_digests))==1
    result=dict(status='passed',created=now(),records=records,all_initial_residual_tensors_identical=True,
        initial_residual_tensor_sha256=initial_digests[0],formal_fit_audited='fitting' in records,
        scope=__doc__,no_task_success_claim=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    atomic_json(args.output,result);print(json.dumps(result))


if __name__=='__main__':main()
