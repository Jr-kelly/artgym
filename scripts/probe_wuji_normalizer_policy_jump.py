"""Measure policy change caused solely by one normalization update.

Use frozen CP10 weights, the same stored training observations and identical
zero RNN state for every counterfactual. No physics steps, reward learning or
test-grasp data are used. This isolates normalization-induced policy drift,
not complete multi-grasp failure or the actual PPO minibatch distribution.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    checkpoint=root/'runs/wuji-goal/verified-policies/teacher-official-timed2-cp10/teacher.pth'
    observations=root/'runs/wuji-goal/diagnostics/functional20-runtime-v2/observations.npz'
    data=np.load(observations)['observations'][:256]
    cfg=configuration('wuji_acquisition_official_timed2',256,
        ['hand=wuji_paper_official_actuator','object=knife_wuji_lowgain_functional20_20260922','test=True'],
        train='wujiAcquisitionSAPG',seed=20261021)
    env,player=make_player(cfg,checkpoint)
    model=player.model;original={k:v.clone() for k,v in model.state_dict().items()}
    batch=torch.as_tensor(data,device=player.device)
    obs=torch.cat([batch,torch.full((256,1),50.,device=player.device)],dim=1)
    outputs=[];rms=model.running_mean_std
    try:
        for condition in ['original','retained_count_update','count1_update']:
            model.load_state_dict(original);model.eval()
            if condition!='original':
                if condition=='count1_update':rms.count.fill_(1.)
                with torch.no_grad():rms.train();rms(batch);rms.eval()
            inputs=dict(is_train=False,prev_actions=None,obs=obs,rnn_states=[v.clone().zero_() for v in player.states])
            with torch.no_grad():result=model(inputs)
            outputs.append(dict(condition=condition,mu=result['mus'].clone(),sigma=result['sigmas'].clone(),count=float(rms.count)))
            for name,value in original.items():
                if not name.startswith('running_mean_std.'):
                    assert torch.equal(model.state_dict()[name],value),name
        base=torch.distributions.Normal(outputs[0]['mu'],outputs[0]['sigma']);rows=[]
        for result in outputs:
            dist=torch.distributions.Normal(result['mu'],result['sigma'])
            kl=torch.distributions.kl_divergence(base,dist).sum(-1)
            delta=(result['mu']-outputs[0]['mu']).abs()
            rows.append(dict(condition=result['condition'],count_after=result['count'],
                gaussian_kl_mean=float(kl.mean()),gaussian_kl_median=float(kl.median()),gaussian_kl_max=float(kl.max()),
                absolute_mean_action_change=float(delta.mean()),absolute_max_action_change=float(delta.max()),
                thumb_mean_change=float(delta[:,16:].mean())))
        model.load_state_dict(original)
        assert all(torch.equal(model.state_dict()[name],value) for name,value in original.items())
        result=dict(status='completed',scope=__doc__,conditions=rows,batch_size=256,
            all_model_tensors_restored=True,learned_weights_unchanged=True,rnn='Identical zeros for every condition',
            checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            observations_sha256=hashlib.sha256(observations.read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
