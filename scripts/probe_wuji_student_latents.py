"""Observe student latent/action errors on a teacher-driven physical rollout.

Every counterfactual uses the same incoming teacher RNN state. Its RNN and RNG
effects are discarded; only the teacher action reaches physics. This isolates
encoder error on successful teacher states, not closed-loop student success.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import wuji_goal_common
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.audit_distillation_runtime import tensor_digest
from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
from isaacgymenvs.eval_common import preprocess_train_config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--students',type=Path,nargs='+',required=True)
    parser.add_argument('--initial-states',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--object',default='knife_wuji_acquisition_precision')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).read_bytes()
    (args.output/'probe_source.py').write_bytes(source)
    original_make=wuji_goal_common.make_player
    frames=[]
    metadata={}
    model_refs=[]

    def make_player(cfg,checkpoint):
        env,player=original_make(cfg,checkpoint)
        env.set_student_encoder_obs_enabled(True)
        network=player.model.a2c_network
        teacher=network.priv_encoder
        model_refs.append(player.model)
        metadata['model_before']=tensor_digest(player.model.state_dict())
        metadata['teacher_sha256']=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
        encoders=[]
        metadata['students']=[]
        for path in args.students:
            artifact=torch.load(path,map_location='cpu');meta=artifact['distill_meta']
            assert meta['teacher_checkpoint_sha256']==metadata['teacher_sha256']
            assert meta['task']=='wuji_acquisition_official_timed2' and meta['hand']=='wuji_paper_official_actuator'
            encoder,*_=build_student_encoder_from_artifact(player,cfg,
                preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),artifact,meta)
            encoder.eval();encoders.append(encoder)
            metadata['students'].append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        original=player.get_action

        def observed(obs,is_deterministic=False,**kwargs):
            incoming=[v.clone() for v in player.states] if player.is_rnn else None
            network.priv_encoder=teacher
            network.actor_encoder_obs_override=None
            teacher_action=original(obs,is_deterministic=is_deterministic,**kwargs)
            outgoing=player.states
            teacher_latent=network.last_privileged_latent.detach().clone()
            cpu_rng=torch.get_rng_state();gpu_rng=torch.cuda.get_rng_state(player.device)
            latent_errors=[];action_errors=[]
            try:
                for encoder in encoders:
                    if player.is_rnn:player.states=[v.clone() for v in incoming]
                    network.priv_encoder=encoder
                    network.actor_encoder_obs_override=env.get_student_encoder_observations()
                    with torch.no_grad():student_action=original(obs,is_deterministic=True,**kwargs)
                    latent_errors.append((network.last_privileged_latent-teacher_latent).detach().cpu().numpy().copy())
                    action_errors.append((student_action-teacher_action).detach().cpu().numpy().copy())
            finally:
                network.priv_encoder=teacher
                network.actor_encoder_obs_override=None
                network.last_privileged_latent=teacher_latent
                player.states=outgoing
                torch.set_rng_state(cpu_rng);torch.cuda.set_rng_state(gpu_rng,player.device)
            frames.append(dict(latent_error=np.stack(latent_errors),action_error=np.stack(action_errors),
                teacher_latent=teacher_latent.detach().cpu().numpy().copy(),
                teacher_action=teacher_action.detach().cpu().numpy().copy(),
                active=env.eval_active_mask.detach().cpu().numpy().copy()))
            return teacher_action

        player.get_action=observed
        return env,player

    wuji_goal_common.make_player=make_player
    from scripts import audit_wuji_timed_commands
    previous=sys.argv
    try:
        sys.argv=[previous[0],'--checkpoint',str(args.checkpoint),'--initial-states',str(args.initial_states),
            '--initial-state-rows']+list(map(str,range(32)))+['--task','wuji_acquisition_official_timed2',
            '--hand','wuji_paper_official_actuator','--object',args.object,'--stage-seconds','2','--seed','1616','--output',str(args.output)]
        audit_wuji_timed_commands.main()
    finally:
        sys.argv=previous
        wuji_goal_common.make_player=original_make
    metadata['model_after']=tensor_digest(model_refs[0].state_dict())
    assert metadata['model_before']==metadata['model_after']
    trace={key:np.stack([row[key] for row in frames]) for key in frames[0]}
    assert trace['latent_error'].shape[:3]==(600,len(args.students),32)
    np.savez_compressed(args.output/'encoder_error_trace.npz',**trace)
    summaries=[]
    for i,path in enumerate(args.students):
        stages=[]
        for stage in range(10):
            active=trace['active'][stage*60:(stage+1)*60]
            latent=trace['latent_error'][stage*60:(stage+1)*60,i][active]
            action=trace['action_error'][stage*60:(stage+1)*60,i][active]
            stages.append(dict(stage=stage,latent_mse=float(np.mean(latent**2)),
                support_action_mae=float(np.mean(abs(action[:,:16]))),
                thumb_action_mae=float(np.mean(abs(action[:,16:]))),
                thumb_increment_error_mrad=float(np.mean(abs(action[:,16:]))*.025*1000)))
        summaries.append(dict(student=str(path),stages=stages))
    metadata.update(status='completed',scope=__doc__,source_sha256=hashlib.sha256(source).hexdigest(),
                    summaries=summaries,steps=len(frames),num_envs=32)
    (args.output/'encoder_report.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata),flush=True)


if __name__=='__main__':
    main()
