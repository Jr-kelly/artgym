"""Small real reset/step audit; local preparation never certifies H200 behavior."""
import argparse
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_env, make_player
import numpy as np
import torch
from scripts.wuji_student_interface import install_legal_public
from scripts.wuji_known_controller import install_known_controller
from scripts.record_wuji_width_goal import R, D
from scripts.wuji_width_contract import ROUND, slots


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--backend',choices=['local-preparation','H200'],required=True)
    p.add_argument('--arm',choices=['C','G'],required=True)
    p.add_argument('--actor-parity',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    if a.backend=='H200':assert 'H200' in torch.cuda.get_device_name(0)
    results=[]
    for arm in [a.arm]:
        cfg=configuration('wuji_width_student',256,['object=knife_wuji_width_train_20261002',
            'hand=wuji_paper_official_actuator','task.env.widthArm='+arm,'task.env.episodeLength=600',
            'task.env.proprioHistoryLen=50','task.env.studentInitObsDim=55','+task.env.enableStudentEncoderObs=True'],train='wujiAcquisitionSAPG',seed=2026100215)
        cfg.task.env.widthTrainingManifest='research/'+ROUND+'/data/'+arm+'-training.json'
        if a.actor_parity:
            assert a.backend=='H200', 'Formal same-backend teacher parity requires H200'
            teacher=R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth'
            env,player=make_player(cfg,teacher);player.model.eval()
            for param in player.model.parameters():param.requires_grad_(False)
        else:env=make_env(cfg)
        try:
            install_legal_public(env);install_known_controller(env,'real')
            env.reset();env.step(torch.zeros((256,20),device=env.device))
            actual=env.env2instance.cpu().tolist();expected=[r['instance'] for r in slots(arm)]
            assert actual==expected
            assert bool(env.instance_grasp_state_pose_is_local.all())
            assert torch.isfinite(env.student_obs_buf).all() and env.student_obs_buf.shape==(256,2076)
            assert torch.allclose(env.init_link0_bbx,env.instance_link0_bbx[env.env2instance])
            assert torch.allclose(env.init_link1_bbx,env.instance_link1_bbx[env.env2instance])
            policy,_=env._compute_sapg_priv_observations()
            expect=env.instance_link0_bbx[env.env2instance][:,[0,2,1]]
            assert torch.allclose(policy[:,49:52],expect,atol=1e-7,rtol=0)
            assert torch.allclose(policy[:,52:55],env.instance_link1_bbx[env.env2instance][:,[0,2,1]],atol=1e-7,rtol=0)
            env.record_width_transitions()
            assert int(env.width_transition_counts.sum())==256
            np.save(a.output/(arm+'-initial55.npy'),policy[:,:55].cpu().numpy())
            parity=None
            if a.actor_parity:
                from isaacgymenvs.distill import normalize_obs_slice
                from isaacgymenvs.utils.distill_action_loss import frozen_actor_mean
                from scripts.wuji_student_interface import legal_policy_observation
                obs=player.env_reset(player.env);incoming=[s.clone() for s in player.states]
                with torch.no_grad():
                    latent=player.model.a2c_network.priv_encoder(normalize_obs_slice(player.model,env.teacher_privileged_obs_buf,111))
                    direct=player.get_action(obs,is_deterministic=True);live_after=[s.clone() for s in player.states]
                    mean=frozen_actor_mean(player,legal_policy_observation(obs),latent,incoming)
                error=float((direct-mean.clamp(-1,1)).abs().max())
                assert error<2e-5
                assert all(torch.equal(x,y) for x,y in zip(live_after,player.states))
                parity=dict(max_action_error=error,tolerance=2e-5,same_public_input=True,same_incoming_rnn=True,live_rnn_unmodified=True)
            results.append(dict(arm=arm,actual_instances=actual,sampler=env.width_receipt(),legal_input_width=2076,teacher_actor_parity=parity,
                initial55_bboxes_verified=True,hand_base_pose_metadata=True,finite_reset_step=True))
        finally:env.gym.destroy_sim(env.sim)
    (a.output/'report.json').write_text(json.dumps(dict(backend=a.backend,device=torch.cuda.get_device_name(0),
        results=results,teacher_parity_checked=a.actor_parity,optimizer_updates=0,
        scope='Actual asset/cache/reset/observation consistency only. H200 actor parity, disposable optimizer updates and formal behavior precheck remain separate'),indent=2)+'\n')


if __name__=='__main__':main()
