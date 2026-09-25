"""Separate small geometry changes, geometry-input shifts and static holding.

observation_only uses nominal physics but intentionally altered bbox input:
it is a counterfactual diagnosis, never honest new-geometry transfer evidence.
static holds initial joint targets; it is not a learned manipulation result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import audit_wuji_timed_commands as evaluator
import numpy as np
import torch
from scripts.audit_distillation_runtime import tensor_digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',required=True)
    parser.add_argument('--geometry-mode',choices=['correct','observation_only','static'],required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stage-seconds',type=int,choices=[2,5],required=True)
    parser.add_argument('--seed',type=int,default=20261051)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'runs/wuji-goal/geometry-sensitivity-20260922/manifest.json').read_text())
    actual=manifest['variants']['nominal' if args.geometry_mode=='observation_only' else args.variant]
    observed=manifest['variants'][args.variant]
    assert hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()=='2230146804f9e0de54d4e61ab3efd2d90ec6ef1ee403130cd9a46c235bf860b7'
    for p,h in actual['artifact_sha256'].items():
        assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
    assert hashlib.sha256((root/actual['states']).read_bytes()).hexdigest()==actual['states_sha256']
    factory=evaluator.make_player
    capture={}
    record=dict(scope=__doc__,mode=args.geometry_mode,variant=args.variant,actual=actual,observed=observed)

    def make_player(cfg,checkpoint):
        env,player=factory(cfg,checkpoint)
        player.model.eval()
        capture.update(player=player,env=env,before=tensor_digest(player.model.state_dict()))
        assert env.object_cfg['asset']['asset_root']=='assets/objects/'+actual['object']
        assert np.allclose(env.instance_link0_bbx.cpu().numpy(),actual['parameters']['handle_size'],rtol=0,atol=1e-7)
        handle=env.gym.find_actor_handle(env.envs[0],'object')
        assert handle>=0
        dofs=env.gym.get_actor_dof_properties(env.envs[0],handle)
        bodies=env.gym.get_actor_rigid_body_properties(env.envs[0],handle)
        masses=[b.mass for b in bodies]
        assert np.allclose(masses,[.029,.006],rtol=1e-5,atol=1e-7)
        assert np.allclose(dofs['damping'],.3) and np.allclose(dofs['stiffness'],0)
        record['actual_properties']=dict(mass=masses,damping=dofs['damping'].tolist(),stiffness=dofs['stiffness'].tolist(),
            inertia=[dict(x=b.inertia.x.x,y=b.inertia.y.y,z=b.inertia.z.z) for b in bodies])
        init_obs=env._get_init_obs
        calls=[0]
        bbox=torch.tensor(observed['parameters']['handle_size'],device=env.device,dtype=torch.float32)
        def get_init_obs():
            value=init_obs()
            assert value.shape[1]==55
            if args.geometry_mode=='observation_only':
                value=value.clone();value[:,49:52]=bbox
            if env.eval_mode:
                assert torch.allclose(value[:,49:52],bbox.expand(env.num_envs,-1),rtol=0,atol=1e-7)
                if not calls[0]:
                    rms=player.model.running_mean_std
                    raw=value[0,49:52]
                    normalized=(raw-rms.running_mean[49:52].float())/torch.sqrt(rms.running_var[49:52].float()+rms.epsilon)
                    record['bbox_normalization']=dict(raw=raw.cpu().tolist(),mean=rms.running_mean[49:52].cpu().tolist(),
                        variance=rms.running_var[49:52].cpu().tolist(),preclip=normalized.cpu().tolist(),clipped=normalized.clamp(-5,5).cpu().tolist())
                calls[0]+=1
            return value
        env._get_init_obs=get_init_obs
        capture['calls']=calls
        if args.geometry_mode=='static':
            count=[0]
            def static_action(obs,is_deterministic=False,**kw):
                count[0]+=1
                return torch.zeros((env.num_envs,20),device=player.device)
            player.get_action=static_action
            capture['static_calls']=count
        return env,player
    evaluator.make_player=make_player
    argv=sys.argv
    try:
        sys.argv=[argv[0],'--checkpoint',str(args.checkpoint),'--output',str(args.output),
            '--task','wuji_acquisition_official_timed2','--hand','wuji_paper_official_actuator',
            '--object',actual['object'],'--initial-states',str(root/actual['states']),
            '--stage-seconds',str(args.stage_seconds),'--seed',str(args.seed)]
        evaluator.main()
        assert tensor_digest(capture['player'].model.state_dict())==capture['before']
        with np.load(args.output/'trace.npz') as trace:
            alive=trace['active'].all(axis=0)&(~trace['fall']).all(axis=0)&(~trace['invalid']).all(axis=0)
            stable=alive&(trace['drift']<.01).all(axis=0)&(trace['rotation']<.25).all(axis=0)
            record['pure_pose_stable_count']=int(stable.sum())
            record['alive_count']=int(alive.sum())
            if args.geometry_mode=='static':
                assert capture['static_calls'][0]==600 and np.all(trace['action']==0)
                assert np.allclose(trace['target'],trace['target'][:1],rtol=0,atol=1e-6)
        record.update(status='passed',model_unchanged=True,geometry_observation_calls=capture['calls'][0],
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output/'geometry-report.json').write_text(json.dumps(record,indent=2)+'\n')
        (args.output/'geometry-source.py').write_bytes(Path(__file__).read_bytes())
        print(json.dumps({k:v for k,v in record.items() if k not in ['actual','observed']}),flush=True)
    finally:
        evaluator.make_player=factory
        sys.argv=argv


if __name__=='__main__':main()
